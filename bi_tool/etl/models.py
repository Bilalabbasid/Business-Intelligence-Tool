"""
ETL Models for Data Ingestion, Processing, and Monitoring
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import JSONField
from djongo import models as mongo_models


class TimestampedModel(models.Model):
    """Abstract base model with timestamp fields."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


# MongoDB Collections for Raw Data
class RawEvent(mongo_models.Model):
    """
    Raw ingested events stored in MongoDB.
    All incoming data goes here first before validation and processing.
    """
    # Unique identifier for deduplication
    ingest_id = mongo_models.CharField(max_length=100, unique=True, db_index=True)
    
    # Source information
    source = mongo_models.CharField(max_length=50, db_index=True)  # 'pos', 'csv_upload', 'api', 'stripe', etc.
    batch_id = mongo_models.CharField(max_length=100, db_index=True)
    branch_id = mongo_models.IntegerField(null=True, blank=True, db_index=True)
    
    # Raw payload
    raw_payload = mongo_models.JSONField()
    
    # Processing metadata
    validation_status = mongo_models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'Pending Validation'),
            ('valid', 'Valid'),
            ('invalid', 'Invalid'),
            ('enriched', 'Valid and Enriched')
        ],
        default='pending',
        db_index=True
    )
    validation_errors = mongo_models.JSONField(default=dict, blank=True)
    
    # Processing flags
    processed = mongo_models.BooleanField(default=False, db_index=True)
    processed_at = mongo_models.DateTimeField(null=True, blank=True, db_index=True)
    etl_run_id = mongo_models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    # Timestamps
    received_at = mongo_models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Enrichment data
    enriched_data = mongo_models.JSONField(default=dict, blank=True)
    
    # Retry and error tracking
    retry_count = mongo_models.IntegerField(default=0)
    last_error = mongo_models.TextField(null=True, blank=True)
    
    class Meta:
        collection = 'raw_events'
        indexes = [
            [('source', 1), ('batch_id', 1)],
            [('validation_status', 1), ('processed', 1)],
            [('received_at', 1)],
            [('branch_id', 1), ('received_at', 1)],
        ]

    def __str__(self):
        return f"{self.source}:{self.ingest_id} ({self.validation_status})"


class RawError(mongo_models.Model):
    """
    Invalid or failed raw events for audit and debugging.
    """
    ingest_id = mongo_models.CharField(max_length=100, db_index=True)
    source = mongo_models.CharField(max_length=50, db_index=True)
    batch_id = mongo_models.CharField(max_length=100, db_index=True)
    
    # Original payload and error details
    raw_payload = mongo_models.JSONField()
    error_type = mongo_models.CharField(max_length=50, db_index=True)  # 'validation', 'schema', 'processing'
    error_message = mongo_models.TextField()
    error_details = mongo_models.JSONField(default=dict)
    
    # Metadata
    failed_at = mongo_models.DateTimeField(auto_now_add=True, db_index=True)
    resolved = mongo_models.BooleanField(default=False, db_index=True)
    resolved_at = mongo_models.DateTimeField(null=True, blank=True)
    resolution_notes = mongo_models.TextField(null=True, blank=True)
    
    class Meta:
        collection = 'raw_errors'
        indexes = [
            [('source', 1), ('error_type', 1)],
            [('failed_at', 1)],
            [('resolved', 1)],
        ]

    def __str__(self):
        return f"Error: {self.source}:{self.ingest_id} - {self.error_type}"


# PostgreSQL Models for ETL Management
class ETLJob(TimestampedModel):
    """
    Definition of ETL jobs and their configurations.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    job_type = models.CharField(
        max_length=30,
        choices=[
            ('ingestion', 'Data Ingestion'),
            ('validation', 'Data Validation'),
            ('transformation', 'Data Transformation'),
            ('aggregation', 'Data Aggregation'),
            ('cleanup', 'Data Cleanup'),
        ],
        db_index=True
    )
    
    # Scheduling
    schedule_type = models.CharField(
        max_length=20,
        choices=[
            ('manual', 'Manual'),
            ('interval', 'Interval-based'),
            ('cron', 'Cron-based'),
            ('event', 'Event-triggered'),
        ],
        default='manual'
    )
    schedule_config = models.JSONField(default=dict, help_text="Cron expression or interval settings")
    
    # Configuration
    source_config = models.JSONField(default=dict, help_text="Source connection and query config")
    target_config = models.JSONField(default=dict, help_text="Target connection and table config")
    transform_config = models.JSONField(default=dict, help_text="Transformation rules and settings")
    
    # Status
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    
    # Dependencies
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True)
    
    class Meta:
        db_table = 'etl_jobs'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.job_type})"


class ETLRun(TimestampedModel):
    """
    Execution history and status of ETL jobs.
    """
    run_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    job = models.ForeignKey(ETLJob, on_delete=models.CASCADE, related_name='runs')
    
    # Execution details
    status = models.CharField(
        max_length=20,
        choices=[
            ('queued', 'Queued'),
            ('running', 'Running'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
            ('retrying', 'Retrying'),
        ],
        default='queued',
        db_index=True
    )
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    # Data processing metrics
    rows_processed = models.BigIntegerField(default=0)
    rows_inserted = models.BigIntegerField(default=0)
    rows_updated = models.BigIntegerField(default=0)
    rows_failed = models.BigIntegerField(default=0)
    rows_skipped = models.BigIntegerField(default=0)
    
    # Error and logging
    error_message = models.TextField(null=True, blank=True)
    log_messages = models.JSONField(default=list)
    
    # Configuration snapshot
    config_snapshot = models.JSONField(default=dict, help_text="Job config at time of execution")
    
    # Data lineage
    source_batches = models.JSONField(default=list, help_text="List of source batch IDs processed")
    checkpoint_before = models.JSONField(default=dict, help_text="Checkpoint before run")
    checkpoint_after = models.JSONField(default=dict, help_text="Checkpoint after run")
    
    # Manual execution metadata
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    trigger_reason = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'etl_runs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.job.name} - {self.run_id} ({self.status})"

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this run."""
        if self.rows_processed == 0:
            return 0.0
        return (self.rows_processed - self.rows_failed) / self.rows_processed * 100


class Checkpoint(TimestampedModel):
    """
    Checkpoints for incremental ETL processing.
    Tracks the last successfully processed position for each source and job.
    """
    job = models.ForeignKey(ETLJob, on_delete=models.CASCADE, related_name='checkpoints')
    source = models.CharField(max_length=50, db_index=True)
    
    # Checkpoint data
    checkpoint_type = models.CharField(
        max_length=20,
        choices=[
            ('timestamp', 'Timestamp-based'),
            ('cursor', 'Cursor/ID-based'),
            ('batch', 'Batch-based'),
            ('sequence', 'Sequence number'),
        ]
    )
    checkpoint_value = models.TextField(help_text="Timestamp, ID, or other checkpoint identifier")
    checkpoint_data = models.JSONField(default=dict, help_text="Additional checkpoint metadata")
    
    # Processing metadata
    last_run = models.ForeignKey(ETLRun, on_delete=models.SET_NULL, null=True, blank=True)
    rows_processed_total = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'etl_checkpoints'
        unique_together = ['job', 'source']
        indexes = [
            models.Index(fields=['job', 'source']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f"{self.job.name}:{self.source} -> {self.checkpoint_value}"


class DataSource(TimestampedModel):
    """
    Configuration for external data sources.
    """
    name = models.CharField(max_length=100, unique=True)
    source_type = models.CharField(
        max_length=30,
        choices=[
            ('database', 'Database Connection'),
            ('api', 'REST API'),
            ('file', 'File Upload'),
            ('webhook', 'Webhook'),
            ('stream', 'Data Stream'),
        ]
    )
    
    # Connection configuration
    connection_config = models.JSONField(
        help_text="Connection parameters (encrypted for sensitive data)"
    )
    
    # Authentication
    auth_type = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Authentication'),
            ('basic', 'Basic Auth'),
            ('token', 'API Token'),
            ('oauth', 'OAuth'),
            ('key', 'API Key'),
        ],
        default='none'
    )
    credentials = models.JSONField(default=dict, help_text="Encrypted credentials")
    
    # Rate limiting and behavior
    rate_limit = models.IntegerField(default=60, help_text="Requests per minute")
    retry_policy = models.JSONField(default=dict, help_text="Retry configuration")
    
    # Status
    is_active = models.BooleanField(default=True)
    last_connected_at = models.DateTimeField(null=True, blank=True)
    connection_status = models.CharField(
        max_length=20,
        choices=[
            ('unknown', 'Unknown'),
            ('connected', 'Connected'),
            ('failed', 'Connection Failed'),
            ('rate_limited', 'Rate Limited'),
        ],
        default='unknown'
    )
    
    # Health monitoring
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    avg_response_time = models.IntegerField(default=0, help_text="Average response time in ms")
    
    class Meta:
        db_table = 'etl_data_sources'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.source_type})"


class AuditLog(TimestampedModel):
    """
    Audit trail for ETL operations and data lineage.
    """
    # Event identification
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('data_ingested', 'Data Ingested'),
            ('data_validated', 'Data Validated'),
            ('data_transformed', 'Data Transformed'),
            ('data_aggregated', 'Data Aggregated'),
            ('job_started', 'Job Started'),
            ('job_completed', 'Job Completed'),
            ('job_failed', 'Job Failed'),
            ('config_changed', 'Configuration Changed'),
        ],
        db_index=True
    )
    
    # Related objects
    job = models.ForeignKey(ETLJob, on_delete=models.CASCADE, null=True, blank=True)
    run = models.ForeignKey(ETLRun, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Event details
    message = models.TextField()
    details = models.JSONField(default=dict)
    
    # Data lineage
    source_table = models.CharField(max_length=100, null=True, blank=True)
    target_table = models.CharField(max_length=100, null=True, blank=True)
    affected_rows = models.BigIntegerField(null=True, blank=True)
    
    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'etl_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['job', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


class ETLAlert(TimestampedModel):
    """
    Alerts and notifications for ETL monitoring.
    """
    alert_type = models.CharField(
        max_length=30,
        choices=[
            ('job_failure', 'Job Failure'),
            ('high_error_rate', 'High Error Rate'),
            ('queue_backlog', 'Queue Backlog'),
            ('data_quality', 'Data Quality Issue'),
            ('connection_failure', 'Connection Failure'),
            ('performance', 'Performance Issue'),
        ],
        db_index=True
    )
    
    # Severity and status
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium',
        db_index=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('acknowledged', 'Acknowledged'),
            ('resolved', 'Resolved'),
            ('suppressed', 'Suppressed'),
        ],
        default='active',
        db_index=True
    )
    
    # Alert details
    title = models.CharField(max_length=200)
    message = models.TextField()
    context = models.JSONField(default=dict)
    
    # Related objects
    job = models.ForeignKey(ETLJob, on_delete=models.CASCADE, null=True, blank=True)
    run = models.ForeignKey(ETLRun, on_delete=models.CASCADE, null=True, blank=True)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)
    
    # Resolution
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)
    
    # Notification tracking
    notifications_sent = models.JSONField(default=list, help_text="List of sent notifications")
    
    class Meta:
        db_table = 'etl_alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['job', 'status']),
        ]

    def __str__(self):
        return f"{self.alert_type} - {self.severity} ({self.status})"