"""
Data Quality Models for BI Tool
Defines models for DQ rules, runs, violations, and configuration.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class DQSeverity(models.TextChoices):
    """Data Quality violation severity levels."""
    INFO = 'INFO', 'Info'
    WARN = 'WARN', 'Warning'
    CRITICAL = 'CRITICAL', 'Critical'


class DQCheckType(models.TextChoices):
    """Types of data quality checks."""
    ROW_COUNT = 'row_count', 'Row Count'
    NULL_RATE = 'null_rate', 'Null Rate'
    UNIQUENESS = 'uniqueness', 'Uniqueness'
    RANGE_CHECK = 'range_check', 'Range Check'
    CARDINALITY = 'cardinality', 'Cardinality'
    REFERENTIAL_INTEGRITY = 'ref_integrity', 'Referential Integrity'
    TIMELINESS = 'timeliness', 'Timeliness/Freshness'
    SCHEMA_DRIFT = 'schema_drift', 'Schema Drift'
    VOLUME_ANOMALY = 'volume_anomaly', 'Volume Anomaly'


class DQRunStatus(models.TextChoices):
    """Status of DQ check runs."""
    PENDING = 'PENDING', 'Pending'
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'
    TIMEOUT = 'TIMEOUT', 'Timeout'


class DQConfig(models.Model):
    """Global configuration for Data Quality system."""
    
    # Alert configuration
    email_enabled = models.BooleanField(default=True)
    slack_enabled = models.BooleanField(default=False)
    pagerduty_enabled = models.BooleanField(default=False)
    
    slack_webhook_url = models.URLField(blank=True, null=True)
    slack_channel_warnings = models.CharField(max_length=50, default='#dq-warnings')
    slack_channel_critical = models.CharField(max_length=50, default='#dq-critical')
    
    pagerduty_integration_key = models.CharField(max_length=255, blank=True, null=True)
    
    # Escalation settings
    critical_escalation_delay_minutes = models.IntegerField(default=15)
    warning_digest_interval_hours = models.IntegerField(default=4)
    
    # Performance settings
    max_concurrent_checks = models.IntegerField(default=10)
    default_query_timeout_seconds = models.IntegerField(default=300)
    default_sample_size = models.IntegerField(default=100)
    
    # Anomaly detection settings
    anomaly_detection_enabled = models.BooleanField(default=True)
    statistical_window_days = models.IntegerField(default=7)
    anomaly_sensitivity = models.FloatField(default=3.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "DQ Configuration"
        verbose_name_plural = "DQ Configurations"
    
    def __str__(self):
        return f"DQ Config - Updated {self.updated_at}"


class DQRule(models.Model):
    """Data Quality rule definition."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    
    # Rule configuration
    check_type = models.CharField(max_length=50, choices=DQCheckType.choices)
    target_database = models.CharField(max_length=50, default='mongodb')  # mongodb, postgres, clickhouse
    target_collection = models.CharField(max_length=100)  # collection/table name
    target_column = models.CharField(max_length=100, blank=True, null=True)
    
    # Check parameters
    query = models.TextField(blank=True, null=True, help_text="Custom query for complex checks")
    threshold = models.FloatField(help_text="Threshold value for the check")
    parameters = models.JSONField(default=dict, help_text="Additional parameters as JSON")
    
    # Metadata
    severity = models.CharField(max_length=10, choices=DQSeverity.choices, default=DQSeverity.WARN)
    # Convert ArrayField to simpler text field for email owners
    owners = models.TextField(default='', help_text="Comma-separated email addresses of rule owners")
    tags = models.TextField(default='', help_text="Comma-separated tags")
    
    # Scheduling
    schedule = models.CharField(max_length=100, help_text="Cron expression for scheduling")
    enabled = models.BooleanField(default=True)
    
    # Execution settings
    timeout_seconds = models.IntegerField(default=300)
    sample_size = models.IntegerField(default=100)
    use_sampling = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_dq_rules')
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['check_type', 'enabled']),
            models.Index(fields=['target_database', 'target_collection']),
            models.Index(fields=['severity', 'enabled']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.check_type})"
    
    @property
    def last_run(self):
        """Get the most recent run for this rule."""
        return self.runs.order_by('-created_at').first()
    
    @property
    def success_rate(self):
        """Calculate success rate over last 30 runs."""
        recent_runs = self.runs.order_by('-created_at')[:30]
        if not recent_runs:
            return None
        
        successful = sum(1 for run in recent_runs if run.status == DQRunStatus.SUCCESS)
        return (successful / len(recent_runs)) * 100


class DQRun(models.Model):
    """Record of a data quality check execution."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(DQRule, on_delete=models.CASCADE, related_name='runs')
    
    # Execution details
    status = models.CharField(max_length=20, choices=DQRunStatus.choices, default=DQRunStatus.PENDING)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    rows_scanned = models.BigIntegerField(default=0)
    violations_count = models.IntegerField(default=0)
    metric_value = models.FloatField(null=True, blank=True, help_text="Actual measured value")
    
    # Execution context
    triggered_by = models.CharField(max_length=50, default='scheduled')  # scheduled, manual, api
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    etl_run_id = models.UUIDField(null=True, blank=True, help_text="Associated ETL run if applicable")
    
    # Logs and metadata
    run_log = models.TextField(blank=True, help_text="Execution logs and debug info")
    error_message = models.TextField(blank=True)
    execution_metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rule', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"{self.rule.name} - {self.status} ({self.started_at})"
    
    @property
    def duration_seconds(self):
        """Calculate run duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_violation(self):
        """Check if this run resulted in violations."""
        return self.violations_count > 0


class DQViolation(models.Model):
    """Individual data quality violation record."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(DQRule, on_delete=models.CASCADE, related_name='violations')
    run = models.ForeignKey(DQRun, on_delete=models.CASCADE, related_name='violations')
    
    # Violation details
    violation_message = models.TextField()
    metric_value = models.FloatField(help_text="Actual value that violated the threshold")
    threshold = models.FloatField(help_text="Expected threshold value")
    severity = models.CharField(max_length=10, choices=DQSeverity.choices)
    
    # Sample data
    target_record_sample = models.JSONField(default=list, help_text="Sample of violating records")
    affected_records_count = models.IntegerField(default=0)
    
    # Resolution tracking
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Alerting
    alert_sent = models.BooleanField(default=False)
    alert_sent_at = models.DateTimeField(null=True, blank=True)
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rule', '-created_at']),
            models.Index(fields=['severity', 'acknowledged']),
            models.Index(fields=['alert_sent', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.rule.name} - {self.severity} ({self.created_at})"
    
    def acknowledge(self, user, notes=""):
        """Acknowledge this violation."""
        self.acknowledged = True
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        if notes:
            self.resolution_notes = notes
        self.save()


class DQAnomalyDetection(models.Model):
    """Anomaly detection results and baselines."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(DQRule, on_delete=models.CASCADE, related_name='anomaly_results')
    
    # Detection parameters
    detection_method = models.CharField(max_length=50, default='statistical')  # statistical, ml_based
    window_days = models.IntegerField(default=7)
    sensitivity = models.FloatField(default=3.0)
    
    # Baseline and results
    baseline_value = models.FloatField(help_text="Baseline/expected value")
    baseline_std = models.FloatField(null=True, help_text="Standard deviation of baseline")
    actual_value = models.FloatField(help_text="Observed value")
    anomaly_score = models.FloatField(help_text="Anomaly score (e.g., z-score)")
    
    is_anomaly = models.BooleanField(default=False)
    confidence = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    # Model metadata (for ML-based detection)
    model_metadata = models.JSONField(default=dict)
    
    detected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['rule', '-detected_at']),
            models.Index(fields=['is_anomaly', '-detected_at']),
        ]
    
    def __str__(self):
        return f"{self.rule.name} - Anomaly: {self.is_anomaly} ({self.detected_at})"


class DQMetric(models.Model):
    """Time-series metrics for DQ monitoring."""
    
    metric_name = models.CharField(max_length=100)
    metric_type = models.CharField(max_length=50)  # counter, gauge, histogram
    value = models.FloatField()
    labels = models.JSONField(default=dict)  # e.g., {"rule": "sales_not_null", "severity": "CRITICAL"}
    
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['metric_name', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.metric_name} = {self.value} ({self.timestamp})"


class DQRuleTemplate(models.Model):
    """Templates for common data quality rules."""
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    check_type = models.CharField(max_length=50, choices=DQCheckType.choices)
    
    # Template configuration
    template_config = models.JSONField(help_text="Template configuration with placeholders")
    required_parameters = models.TextField(default='', help_text="Comma-separated required parameters")
    
    # Metadata
    category = models.CharField(max_length=50, default='general')
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.check_type})"