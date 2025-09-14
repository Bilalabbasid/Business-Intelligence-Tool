"""
Django Admin Configuration for Data Quality Models
Provides admin interface for managing DQ rules, runs, violations, and configurations.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta

from .models import (
    DQRule, DQRun, DQViolation, DQMetric, DQConfig,
    DQAnomalyDetection, DQRuleTemplate
)
from .tasks import execute_dq_check


@admin.register(DQRule)
class DQRuleAdmin(admin.ModelAdmin):
    """Admin interface for DQ Rules."""
    
    list_display = [
        'name', 'check_type', 'severity', 'target_database', 'target_collection',
        'enabled', 'last_run_status', 'recent_violations', 'created_at'
    ]
    
    list_filter = [
        'check_type', 'severity', 'enabled', 'target_database', 'created_at'
    ]
    
    search_fields = ['name', 'description', 'target_collection', 'owners']
    
    readonly_fields = ['created_at', 'updated_at', 'last_run_info', 'violation_summary']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'enabled')
        }),
        ('Check Configuration', {
            'fields': (
                'check_type', 'target_database', 'target_collection', 'target_column',
                'threshold', 'severity', 'query', 'parameters'
            )
        }),
        ('Scheduling & Execution', {
            'fields': ('schedule', 'timeout_seconds', 'sample_size', 'use_sampling')
        }),
        ('Ownership & Tagging', {
            'fields': ('owners', 'tags')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'last_run_info', 'violation_summary'),
            'classes': ['collapse']
        })
    )
    
    actions = ['enable_rules', 'disable_rules', 'execute_rules']
    
    def last_run_status(self, obj):
        """Display last run status with color coding."""
        last_run = obj.runs.order_by('-finished_at').first()
        if not last_run:
            return format_html('<span style="color: gray;">Never run</span>')
        
        color_map = {
            'SUCCESS': 'green',
            'FAILED': 'red',
            'RUNNING': 'orange'
        }
        
        color = color_map.get(last_run.status, 'gray')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            last_run.status
        )
    
    def recent_violations(self, obj):
        """Count of violations in last 24 hours."""
        since_time = timezone.now() - timedelta(hours=24)
        count = obj.violations.filter(detected_at__gte=since_time).count()
        
        if count == 0:
            return format_html('<span style="color: green;">0</span>')
        elif count < 10:
            return format_html('<span style="color: orange;">{}</span>', count)
        else:
            return format_html('<span style="color: red;">{}</span>', count)
    
    def last_run_info(self, obj):
        """Detailed info about last run."""
        last_run = obj.runs.order_by('-finished_at').first()
        if not last_run:
            return "No runs yet"
        
        return format_html(
            'Status: <strong>{}</strong><br>'
            'Finished: {}<br>'
            'Duration: {} seconds<br>'
            'Violations: {}<br>'
            'Rows Scanned: {}',
            last_run.status,
            last_run.finished_at.strftime('%Y-%m-%d %H:%M:%S') if last_run.finished_at else 'N/A',
            last_run.duration_seconds or 'N/A',
            last_run.violations_count or 0,
            last_run.rows_scanned or 'N/A'
        )
    
    def violation_summary(self, obj):
        """Summary of violations by severity."""
        violations = obj.violations.values('severity').annotate(count=Count('id'))
        if not violations:
            return "No violations"
        
        summary_parts = []
        for v in violations:
            summary_parts.append(f"{v['severity']}: {v['count']}")
        
        return ", ".join(summary_parts)
    
    def enable_rules(self, request, queryset):
        """Enable selected rules."""
        count = queryset.update(enabled=True)
        self.message_user(request, f'Enabled {count} rules.')
    enable_rules.short_description = "Enable selected rules"
    
    def disable_rules(self, request, queryset):
        """Disable selected rules."""
        count = queryset.update(enabled=False)
        self.message_user(request, f'Disabled {count} rules.')
    disable_rules.short_description = "Disable selected rules"
    
    def execute_rules(self, request, queryset):
        """Execute selected rules."""
        for rule in queryset.filter(enabled=True):
            execute_dq_check.delay(rule.id)
        
        enabled_count = queryset.filter(enabled=True).count()
        self.message_user(request, f'Queued {enabled_count} rules for execution.')
    execute_rules.short_description = "Execute selected rules"


@admin.register(DQRun)
class DQRunAdmin(admin.ModelAdmin):
    """Admin interface for DQ Runs."""
    
    list_display = [
        'id', 'rule_link', 'status', 'started_at', 'completed_at',
        'duration_seconds', 'violations_count', 'triggered_by'
    ]
    
    list_filter = [
        'status', 'rule__check_type', 'rule__severity', 'triggered_by', 'started_at'
    ]
    
    search_fields = ['rule__name', 'triggered_by', 'error_message']
    
    readonly_fields = [
        'started_at', 'completed_at', 'duration_seconds',
        'result_details_formatted', 'violation_links'
    ]
    
    fieldsets = (
        ('Run Information', {
            'fields': ('rule', 'status', 'triggered_by')
        }),
        ('Timing', {
            'fields': ('started_at', 'finished_at', 'duration_seconds')
        }),
        ('Results', {
            'fields': ('rows_scanned', 'violations_count', 'error_message')
        }),
        ('Details', {
            'fields': ('result_details_formatted', 'violation_links'),
            'classes': ['collapse']
        })
    )
    
    date_hierarchy = 'started_at'
    
    def rule_link(self, obj):
        """Link to the associated rule."""
        url = reverse('admin:dq_dqrule_change', args=[obj.rule.id])
        return format_html('<a href="{}">{}</a>', url, obj.rule.name)
    rule_link.short_description = 'Rule'
    
    def result_details_formatted(self, obj):
        """Formatted display of result details."""
        if not obj.result_details:
            return "No details available"
        
        import json
        try:
            formatted = json.dumps(obj.result_details, indent=2)
            return format_html('<pre>{}</pre>', formatted)
        except Exception:
            return str(obj.result_details)
    result_details_formatted.short_description = 'Result Details'
    
    def violation_links(self, obj):
        """Links to violations for this run."""
        violations = obj.violations.all()[:10]  # Limit to 10
        
        if not violations:
            return "No violations"
        
        links = []
        for violation in violations:
            url = reverse('admin:dq_dqviolation_change', args=[violation.id])
            links.append(f'<a href="{url}">Violation #{violation.id}</a>')
        
        more_count = obj.violations.count() - 10
        if more_count > 0:
            links.append(f'... and {more_count} more')
        
        return format_html('<br>'.join(links))
    violation_links.short_description = 'Related Violations'


@admin.register(DQViolation)
class DQViolationAdmin(admin.ModelAdmin):
    """Admin interface for DQ Violations."""
    
    list_display = [
        'id', 'rule_link', 'violation_type', 'severity', 'detected_at',
        'acknowledged', 'acknowledged_by'
    ]
    
    list_filter = [
        'severity', 'acknowledged', 'rule__check_type', 'detected_at'
    ]
    
    search_fields = [
        'rule__name', 'violation_type', 'description',
        'acknowledged_by', 'acknowledgment_note'
    ]
    
    readonly_fields = [
        'rule', 'run', 'detected_at', 'sample_data_formatted', 'metadata_formatted'
    ]
    
    fieldsets = (
        ('Violation Information', {
            'fields': ('rule', 'run', 'violation_type', 'description', 'severity')
        }),
        ('Detection', {
            'fields': ('detected_at', 'sample_data_formatted', 'metadata_formatted')
        }),
        ('Acknowledgment', {
            'fields': ('acknowledged', 'acknowledged_by', 'acknowledged_at', 'acknowledgment_note')
        })
    )
    
    date_hierarchy = 'detected_at'
    
    actions = ['acknowledge_violations', 'unacknowledge_violations']
    
    def rule_link(self, obj):
        """Link to the associated rule."""
        url = reverse('admin:dq_dqrule_change', args=[obj.rule.id])
        return format_html('<a href="{}">{}</a>', url, obj.rule.name)
    rule_link.short_description = 'Rule'
    
    def sample_data_formatted(self, obj):
        """Formatted display of sample data."""
        if not obj.sample_data:
            return "No sample data"
        
        import json
        try:
            formatted = json.dumps(obj.sample_data, indent=2)
            return format_html('<pre>{}</pre>', formatted)
        except Exception:
            return str(obj.sample_data)
    sample_data_formatted.short_description = 'Sample Data'
    
    def metadata_formatted(self, obj):
        """Formatted display of metadata."""
        if not obj.metadata:
            return "No metadata"
        
        import json
        try:
            formatted = json.dumps(obj.metadata, indent=2)
            return format_html('<pre>{}</pre>', formatted)
        except Exception:
            return str(obj.metadata)
    metadata_formatted.short_description = 'Metadata'
    
    def acknowledge_violations(self, request, queryset):
        """Acknowledge selected violations."""
        count = queryset.filter(acknowledged=False).update(
            acknowledged=True,
            acknowledged_by=request.user.username,
            acknowledged_at=timezone.now()
        )
        self.message_user(request, f'Acknowledged {count} violations.')
    acknowledge_violations.short_description = "Acknowledge selected violations"
    
    def unacknowledge_violations(self, request, queryset):
        """Unacknowledge selected violations."""
        count = queryset.update(
            acknowledged=False,
            acknowledged_by=None,
            acknowledged_at=None,
            acknowledgment_note=''
        )
        self.message_user(request, f'Unacknowledged {count} violations.')
    unacknowledge_violations.short_description = "Unacknowledge selected violations"


@admin.register(DQMetric)
class DQMetricAdmin(admin.ModelAdmin):
    """Admin interface for DQ Metrics."""
    
    list_display = [
        'id', 'rule_link', 'metric_name', 'metric_value', 'recorded_at'
    ]
    
    list_filter = ['metric_name', 'rule__name', 'recorded_at']
    
    search_fields = ['rule__name', 'metric_name', 'tags']
    
    readonly_fields = ['recorded_at', 'tags_formatted']
    
    date_hierarchy = 'recorded_at'
    
    def rule_link(self, obj):
        """Link to the associated rule."""
        url = reverse('admin:dq_dqrule_change', args=[obj.rule.id])
        return format_html('<a href="{}">{}</a>', url, obj.rule.name)
    rule_link.short_description = 'Rule'
    
    def tags_formatted(self, obj):
        """Formatted display of tags."""
        if not obj.tags:
            return "No tags"
        
        import json
        try:
            formatted = json.dumps(obj.tags, indent=2)
            return format_html('<pre>{}</pre>', formatted)
        except Exception:
            return str(obj.tags)
    tags_formatted.short_description = 'Tags'


@admin.register(DQConfig)
class DQConfigAdmin(admin.ModelAdmin):
    """Admin interface for DQ Configuration."""
    
    list_display = ['key', 'description', 'is_encrypted', 'updated_at']
    
    list_filter = ['is_encrypted', 'updated_at']
    
    search_fields = ['key', 'description']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('key', 'value', 'description', 'is_encrypted')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        })
    )


@admin.register(DQAnomalyDetection)
class DQAnomalyDetectionAdmin(admin.ModelAdmin):
    """Admin interface for DQ Anomaly Detection."""
    
    list_display = [
        'id', 'rule_link', 'detection_method', 'anomaly_score',
        'actual_value', 'detected_at'
    ]
    
    list_filter = ['detection_method', 'detected_at', 'rule__name']
    
    search_fields = ['rule__name', 'detection_method']
    
    readonly_fields = ['detected_at', 'context_formatted']
    
    date_hierarchy = 'detected_at'
    
    def rule_link(self, obj):
        """Link to the associated rule."""
        url = reverse('admin:dq_dqrule_change', args=[obj.rule.id])
        return format_html('<a href="{}">{}</a>', url, obj.rule.name)
    rule_link.short_description = 'Rule'
    
    def context_formatted(self, obj):
        """Formatted display of context data."""
        if not obj.context:
            return "No context"
        
        import json
        try:
            formatted = json.dumps(obj.context, indent=2)
            return format_html('<pre>{}</pre>', formatted)
        except Exception:
            return str(obj.context)
    context_formatted.short_description = 'Context'


@admin.register(DQRuleTemplate)
class DQRuleTemplateAdmin(admin.ModelAdmin):
    """Admin interface for DQ Rule Templates."""
    
    list_display = [
        'name', 'category', 'check_type', 'enabled', 'usage_count', 'created_at'
    ]
    
    list_filter = ['category', 'check_type', 'enabled', 'created_at']
    
    search_fields = ['name', 'description', 'tags']
    
    readonly_fields = ['usage_count', 'created_at', 'updated_at', 'template_config_formatted']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'category', 'description', 'enabled')
        }),
        ('Configuration', {
            'fields': (
                'check_type', 'default_threshold', 'default_severity',
                'template_config_formatted', 'tags'
            )
        }),
        ('Usage & Audit', {
            'fields': ('usage_count', 'created_at', 'updated_at'),
            'classes': ['collapse']
        })
    )
    
    def template_config_formatted(self, obj):
        """Formatted display of template configuration."""
        if not obj.template_config:
            return "No configuration"
        
        import json
        try:
            formatted = json.dumps(obj.template_config, indent=2)
            return format_html('<pre>{}</pre>', formatted)
        except Exception:
            return str(obj.template_config)
    template_config_formatted.short_description = 'Template Configuration'


# Custom admin site configuration
admin.site.site_header = "BI Platform Data Quality Administration"
admin.site.site_title = "DQ Admin"
admin.site.index_title = "Data Quality Management"