"""
Django admin configuration for PII models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    PIICategory, PIIDataMap, DataSubject, DataSubjectRequest,
    ConsentRecord, PIIProcessingRecord, RetentionPolicy
)


@admin.register(PIICategory)
class PIICategoryAdmin(admin.ModelAdmin):
    """Admin interface for PII categories."""
    
    list_display = ['name', 'sensitivity_level', 'retention_period_days', 'is_active']
    list_filter = ['sensitivity_level', 'is_active']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'sensitivity_level', 'is_active')
        }),
        ('Compliance', {
            'fields': ('regulatory_requirements', 'retention_period_days')
        })
    )


@admin.register(PIIDataMap)
class PIIDataMapAdmin(admin.ModelAdmin):
    """Admin interface for PII data mapping."""
    
    list_display = ['get_full_path', 'category', 'pii_type', 'is_encrypted', 'is_compliant', 'confidence_score']
    list_filter = ['category', 'pii_type', 'is_encrypted', 'is_compliant', 'discovery_method']
    search_fields = ['database_name', 'table_name', 'column_name', 'pii_type']
    
    fieldsets = (
        ('Data Location', {
            'fields': ('database_name', 'table_name', 'column_name')
        }),
        ('Classification', {
            'fields': ('category', 'pii_type', 'confidence_score')
        }),
        ('Security', {
            'fields': ('is_encrypted', 'encryption_key_id', 'is_tokenized')
        }),
        ('Discovery', {
            'fields': ('discovered_at', 'discovery_method')
        }),
        ('Compliance', {
            'fields': ('is_compliant', 'compliance_notes', 'last_verified')
        }),
        ('Metadata', {
            'fields': ('sample_data', 'record_count', 'metadata'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_verified', 'mark_compliant']
    
    def mark_verified(self, request, queryset):
        """Mark selected data maps as verified."""
        queryset.update(last_verified=timezone.now())
        self.message_user(request, f"Marked {queryset.count()} data maps as verified.")
    mark_verified.short_description = "Mark selected as verified"
    
    def mark_compliant(self, request, queryset):
        """Mark selected data maps as compliant."""
        queryset.update(is_compliant=True, last_verified=timezone.now())
        self.message_user(request, f"Marked {queryset.count()} data maps as compliant.")
    mark_compliant.short_description = "Mark selected as compliant"


@admin.register(DataSubject)
class DataSubjectAdmin(admin.ModelAdmin):
    """Admin interface for data subjects."""
    
    list_display = ['subject_id', 'email', 'consent_given', 'deletion_requested', 'is_active']
    list_filter = ['consent_given', 'deletion_requested', 'is_active', 'consent_date']
    search_fields = ['subject_id', 'email', 'external_id']
    
    fieldsets = (
        ('Subject Information', {
            'fields': ('subject_id', 'external_id', 'email', 'phone', 'name')
        }),
        ('Consent Management', {
            'fields': ('consent_given', 'consent_date', 'consent_version', 'consent_source')
        }),
        ('Rights Exercised', {
            'fields': ('has_requested_access', 'has_requested_deletion', 'has_requested_portability', 'has_objected_processing')
        }),
        ('Status', {
            'fields': ('is_active', 'deletion_requested', 'deletion_scheduled')
        }),
        ('Processing Details', {
            'fields': ('data_sources', 'processing_purposes', 'legal_basis', 'metadata'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['schedule_deletion']
    
    def schedule_deletion(self, request, queryset):
        """Schedule deletion for selected data subjects."""
        from datetime import timedelta
        deletion_date = timezone.now() + timedelta(days=30)
        queryset.update(deletion_requested=True, deletion_scheduled=deletion_date)
        self.message_user(request, f"Scheduled deletion for {queryset.count()} data subjects.")
    schedule_deletion.short_description = "Schedule for deletion (30 days)"


@admin.register(DataSubjectRequest)
class DataSubjectRequestAdmin(admin.ModelAdmin):
    """Admin interface for data subject requests."""
    
    list_display = ['request_id', 'subject', 'request_type', 'status', 'priority', 'due_date', 'is_overdue_display']
    list_filter = ['request_type', 'status', 'priority', 'received_date']
    search_fields = ['request_id', 'subject__subject_id', 'subject__email']
    date_hierarchy = 'received_date'
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_id', 'subject', 'request_type', 'description')
        }),
        ('Processing', {
            'fields': ('status', 'assigned_to', 'priority')
        }),
        ('Dates', {
            'fields': ('received_date', 'due_date', 'verified_date', 'completed_date')
        }),
        ('Response', {
            'fields': ('response_data', 'response_files', 'rejection_reason')
        }),
        ('Notes', {
            'fields': ('processing_notes',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['request_id', 'received_date']
    
    def is_overdue_display(self, obj):
        """Display if request is overdue."""
        if obj.is_overdue():
            return format_html('<span style="color: red;">Yes</span>')
        return "No"
    is_overdue_display.short_description = "Overdue"
    
    def get_queryset(self, request):
        """Order by due date."""
        qs = super().get_queryset(request)
        return qs.order_by('due_date')


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    """Admin interface for consent records."""
    
    list_display = ['subject', 'purpose', 'is_active', 'given_date', 'expiry_date']
    list_filter = ['purpose', 'legal_basis', 'is_active', 'given_date']
    search_fields = ['subject__subject_id', 'subject__email', 'purpose']
    date_hierarchy = 'given_date'
    
    fieldsets = (
        ('Consent Information', {
            'fields': ('subject', 'purpose', 'legal_basis', 'consent_text', 'consent_version')
        }),
        ('Status', {
            'fields': ('is_active', 'given_date', 'withdrawn_date', 'expiry_date')
        }),
        ('Context', {
            'fields': ('source', 'ip_address', 'user_agent')
        })
    )
    
    readonly_fields = ['given_date']


@admin.register(PIIProcessingRecord)
class PIIProcessingRecordAdmin(admin.ModelAdmin):
    """Admin interface for PII processing records."""
    
    list_display = ['subject_display', 'processing_type', 'purpose', 'system', 'performed_at', 'is_compliant']
    list_filter = ['processing_type', 'is_compliant', 'system', 'performed_at']
    search_fields = ['subject__subject_id', 'purpose', 'system']
    date_hierarchy = 'performed_at'
    
    fieldsets = (
        ('Processing Details', {
            'fields': ('subject', 'processing_type', 'purpose', 'legal_basis')
        }),
        ('Data Information', {
            'fields': ('data_categories', 'data_sources', 'data_recipients')
        }),
        ('Technical Details', {
            'fields': ('system', 'processor', 'performed_by', 'performed_at')
        }),
        ('Compliance', {
            'fields': ('is_compliant', 'compliance_notes')
        })
    )
    
    readonly_fields = ['performed_at']
    
    def subject_display(self, obj):
        """Display subject information."""
        if obj.subject:
            return f"{obj.subject.subject_id}"
        return "System Process"
    subject_display.short_description = "Subject"


@admin.register(RetentionPolicy)
class RetentionPolicyAdmin(admin.ModelAdmin):
    """Admin interface for retention policies."""
    
    list_display = ['name', 'category', 'retention_period_days', 'action_after_retention', 'is_active']
    list_filter = ['action_after_retention', 'is_active', 'category']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Policy Information', {
            'fields': ('name', 'description', 'category', 'is_active')
        }),
        ('Retention Rules', {
            'fields': ('retention_period_days', 'action_after_retention')
        }),
        ('Exceptions', {
            'fields': ('legal_hold_override', 'regulatory_requirements')
        })
    )