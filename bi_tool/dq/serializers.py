"""
Data Quality API Serializers
Serializers for DQ models and API responses.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    DQRule, DQRun, DQViolation, DQMetric, DQConfig, 
    DQAnomalyDetection, DQRuleTemplate, DQCheckType, DQSeverity
)


class DQRuleSerializer(serializers.ModelSerializer):
    """Serializer for DQ Rule model."""
    
    check_type_display = serializers.CharField(source='get_check_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    last_run = serializers.SerializerMethodField()
    recent_violations = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = DQRule
        fields = [
            'id', 'name', 'description', 'check_type', 'check_type_display',
            'target_database', 'target_collection', 'target_column',
            'threshold', 'severity', 'severity_display', 'schedule',
            'enabled', 'owners', 'tags', 'query', 'parameters',
            'timeout_seconds', 'sample_size', 'use_sampling',
            'created_at', 'updated_at', 'last_run', 'recent_violations',
            'success_rate'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_last_run(self, obj):
        """Get last run information."""
        last_run = obj.runs.order_by('-finished_at').first()
        if last_run:
            return {
                'id': last_run.id,
                'status': last_run.status,
                'finished_at': last_run.finished_at,
                'violations_count': last_run.violations_count,
                'duration_seconds': last_run.duration_seconds
            }
        return None
    
    def get_recent_violations(self, obj):
        """Get count of recent violations (last 24 hours)."""
        from django.utils import timezone
        from datetime import timedelta
        
        since_time = timezone.now() - timedelta(hours=24)
        return obj.violations.filter(detected_at__gte=since_time).count()
    
    def get_success_rate(self, obj):
        """Calculate success rate for recent runs."""
        recent_runs = obj.runs.order_by('-finished_at')[:10]
        if not recent_runs:
            return None
        
        successful = sum(1 for run in recent_runs if run.status == 'SUCCESS')
        return round((successful / len(recent_runs)) * 100, 1)


class DQRuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating DQ rules."""
    
    class Meta:
        model = DQRule
        fields = [
            'name', 'description', 'check_type', 'target_database',
            'target_collection', 'target_column', 'threshold', 'severity',
            'schedule', 'enabled', 'owners', 'tags', 'query', 'parameters',
            'timeout_seconds', 'sample_size', 'use_sampling'
        ]
    
    def validate_check_type(self, value):
        """Validate check type."""
        valid_types = [choice[0] for choice in DQCheckType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid check type. Must be one of: {valid_types}")
        return value
    
    def validate_severity(self, value):
        """Validate severity."""
        valid_severities = [choice[0] for choice in DQSeverity.choices]
        if value not in valid_severities:
            raise serializers.ValidationError(f"Invalid severity. Must be one of: {valid_severities}")
        return value
    
    def validate_threshold(self, value):
        """Validate threshold value."""
        if value < 0:
            raise serializers.ValidationError("Threshold must be non-negative")
        return value
    
    def validate_schedule(self, value):
        """Validate cron schedule format."""
        if value:
            parts = value.split()
            if len(parts) != 5:
                raise serializers.ValidationError("Schedule must be in cron format (5 fields)")
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        check_type = data.get('check_type')
        
        # Check type specific validations
        if check_type in ['null_rate', 'uniqueness', 'range_check'] and not data.get('target_column'):
            raise serializers.ValidationError(
                f"target_column is required for check_type: {check_type}"
            )
        
        if check_type == 'ref_integrity':
            parameters = data.get('parameters', {})
            required_params = ['ref_database', 'ref_table', 'ref_column']
            missing_params = [p for p in required_params if p not in parameters]
            if missing_params:
                raise serializers.ValidationError(
                    f"ref_integrity check requires parameters: {missing_params}"
                )
        
        return data


class DQRunSerializer(serializers.ModelSerializer):
    """Serializer for DQ Run model."""
    
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    rule_check_type = serializers.CharField(source='rule.check_type', read_only=True)
    rule_severity = serializers.CharField(source='rule.severity', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    violations = serializers.SerializerMethodField()
    
    class Meta:
        model = DQRun
        fields = [
            'id', 'rule', 'rule_name', 'rule_check_type', 'rule_severity',
            'status', 'status_display', 'started_at', 'finished_at',
            'duration_seconds', 'rows_scanned', 'violations_count',
            'triggered_by', 'error_message', 'result_details', 'violations'
        ]
    
    def get_violations(self, obj):
        """Get violations for this run (if requested)."""
        if hasattr(obj, 'include_violations') and obj.include_violations:
            violations = obj.violations.all()[:10]  # Limit to 10
            return DQViolationSerializer(violations, many=True, context=self.context).data
        return None


class DQRunSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for DQ runs in summaries."""
    
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    
    class Meta:
        model = DQRun
        fields = [
            'id', 'rule_name', 'status', 'finished_at',
            'violations_count', 'duration_seconds'
        ]


class DQViolationSerializer(serializers.ModelSerializer):
    """Serializer for DQ Violation model."""
    
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    rule_check_type = serializers.CharField(source='rule.check_type', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = DQViolation
        fields = [
            'id', 'rule', 'rule_name', 'rule_check_type', 'run',
            'violation_type', 'description', 'severity', 'severity_display',
            'detected_at', 'sample_data', 'metadata', 'acknowledged',
            'acknowledged_by', 'acknowledged_at', 'acknowledgment_note'
        ]
        read_only_fields = [
            'detected_at', 'acknowledged_by', 'acknowledged_at'
        ]


class DQMetricSerializer(serializers.ModelSerializer):
    """Serializer for DQ Metric model."""
    
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    
    class Meta:
        model = DQMetric
        fields = [
            'id', 'rule', 'rule_name', 'run', 'metric_name',
            'metric_value', 'tags', 'recorded_at'
        ]


class DQConfigSerializer(serializers.ModelSerializer):
    """Serializer for DQ Config model."""
    
    class Meta:
        model = DQConfig
        fields = [
            'id', 'key', 'value', 'description', 'is_encrypted',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_key(self, value):
        """Ensure config key follows naming convention."""
        if not value.startswith('dq.'):
            raise serializers.ValidationError("Config keys must start with 'dq.'")
        return value


class DQAnomalyDetectionSerializer(serializers.ModelSerializer):
    """Serializer for DQ Anomaly Detection model."""
    
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    
    class Meta:
        model = DQAnomalyDetection
        fields = [
            'id', 'rule', 'rule_name', 'run', 'detection_method',
            'anomaly_score', 'threshold_value', 'actual_value',
            'expected_range_min', 'expected_range_max', 'context',
            'detected_at'
        ]


class DQRuleTemplateSerializer(serializers.ModelSerializer):
    """Serializer for DQ Rule Template model."""
    
    check_type_display = serializers.CharField(source='get_check_type_display', read_only=True)
    
    class Meta:
        model = DQRuleTemplate
        fields = [
            'id', 'name', 'category', 'description', 'check_type',
            'check_type_display', 'template_config', 'default_threshold',
            'default_severity', 'tags', 'enabled', 'usage_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['usage_count', 'created_at', 'updated_at']


class DQRuleFromTemplateSerializer(serializers.Serializer):
    """Serializer for creating a rule from template."""
    
    template_id = serializers.IntegerField()
    rule_name = serializers.CharField(max_length=255)
    target_database = serializers.CharField(max_length=50)
    target_collection = serializers.CharField(max_length=255)
    target_column = serializers.CharField(max_length=255, required=False, allow_blank=True)
    threshold = serializers.FloatField(required=False)
    severity = serializers.ChoiceField(
        choices=DQSeverity.choices,
        required=False
    )
    schedule = serializers.CharField(max_length=100, required=False, default='0 */4 * * *')
    owners = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    parameters = serializers.JSONField(required=False, default=dict)
    
    def validate_template_id(self, value):
        """Validate template exists and is enabled."""
        try:
            template = DQRuleTemplate.objects.get(id=value, enabled=True)
            return value
        except DQRuleTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found or disabled")
    
    def create(self, validated_data):
        """Create DQ rule from template."""
        template = DQRuleTemplate.objects.get(id=validated_data['template_id'])
        
        # Merge template config with provided data
        rule_data = template.template_config.copy()
        rule_data.update({
            'name': validated_data['rule_name'],
            'target_database': validated_data['target_database'],
            'target_collection': validated_data['target_collection'],
            'target_column': validated_data.get('target_column', ''),
            'threshold': validated_data.get('threshold', template.default_threshold),
            'severity': validated_data.get('severity', template.default_severity),
            'schedule': validated_data.get('schedule', '0 */4 * * *'),
            'owners': validated_data.get('owners', []),
            'tags': validated_data.get('tags', []),
            'parameters': validated_data.get('parameters', {}),
            'check_type': template.check_type,
            'description': f"Generated from template: {template.name}"
        })
        
        # Create rule
        rule = DQRule.objects.create(**rule_data)
        
        # Update template usage count
        template.usage_count += 1
        template.save()
        
        return rule


class DQDashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary data."""
    
    total_rules = serializers.IntegerField()
    enabled_rules = serializers.IntegerField()
    recent_runs = serializers.IntegerField()
    recent_violations = serializers.IntegerField()
    success_rate = serializers.FloatField()
    top_failing_rules = serializers.ListField()
    violation_trend = serializers.ListField()
    
    
class DQRuleSuggestionSerializer(serializers.Serializer):
    """Serializer for rule suggestions."""
    
    suggested_name = serializers.CharField()
    check_type = serializers.CharField()
    target_column = serializers.CharField(required=False, allow_blank=True)
    threshold = serializers.FloatField()
    severity = serializers.CharField()
    description = serializers.CharField()
    confidence = serializers.FloatField()
    rationale = serializers.CharField()


class DQAlertConfigSerializer(serializers.Serializer):
    """Serializer for alert configuration."""
    
    email_enabled = serializers.BooleanField(default=True)
    slack_enabled = serializers.BooleanField(default=False)
    pagerduty_enabled = serializers.BooleanField(default=False)
    
    email_recipients = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list
    )
    
    slack_webhook = serializers.URLField(required=False, allow_blank=True)
    pagerduty_integration_key = serializers.CharField(required=False, allow_blank=True)
    
    severity_thresholds = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        default=dict
    )
    
    escalation_rules = serializers.JSONField(required=False, default=dict)


class DQBulkOperationSerializer(serializers.Serializer):
    """Serializer for bulk operations on DQ rules."""
    
    rule_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    
    operation = serializers.ChoiceField(
        choices=['enable', 'disable', 'delete', 'execute', 'update_schedule']
    )
    
    parameters = serializers.JSONField(required=False, default=dict)
    
    def validate_rule_ids(self, value):
        """Validate that all rule IDs exist."""
        existing_ids = set(
            DQRule.objects.filter(id__in=value).values_list('id', flat=True)
        )
        invalid_ids = set(value) - existing_ids
        
        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid rule IDs: {list(invalid_ids)}"
            )
        
        return value


class DQExportRequestSerializer(serializers.Serializer):
    """Serializer for data export requests."""
    
    export_type = serializers.ChoiceField(
        choices=['rules', 'runs', 'violations', 'metrics']
    )
    
    format = serializers.ChoiceField(
        choices=['csv', 'json', 'yaml'],
        default='csv'
    )
    
    filters = serializers.JSONField(required=False, default=dict)
    
    date_range = serializers.JSONField(required=False, default=dict)
    
    limit = serializers.IntegerField(
        min_value=1,
        max_value=100000,
        default=10000
    )