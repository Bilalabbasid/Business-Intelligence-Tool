"""
PII management models for tracking, auditing, and managing personal data.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional

from core.models import BaseModel

User = get_user_model()


class PIICategory(BaseModel):
    """Categories for classifying PII data."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    sensitivity_level = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low Sensitivity'),
            ('MEDIUM', 'Medium Sensitivity'),
            ('HIGH', 'High Sensitivity'),
            ('CRITICAL', 'Critical Sensitivity'),
        ],
        default='MEDIUM'
    )
    regulatory_requirements = models.TextField(default='[]')  # JSON as text field
    retention_period_days = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "PII Categories"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.sensitivity_level})"


class PIIDataMap(BaseModel):
    """Maps PII data locations across the system."""
    
    # Data location information
    database_name = models.CharField(max_length=100)
    table_name = models.CharField(max_length=100)
    column_name = models.CharField(max_length=100)
    
    # PII classification
    category = models.ForeignKey(PIICategory, on_delete=models.CASCADE)
    pii_type = models.CharField(max_length=100)  # email, phone, ssn, etc.
    
    # Data characteristics
    is_encrypted = models.BooleanField(default=False)
    encryption_key_id = models.CharField(max_length=100, null=True, blank=True)
    is_tokenized = models.BooleanField(default=False)
    
    # Discovery information
    discovered_at = models.DateTimeField()
    discovery_method = models.CharField(
        max_length=20,
        choices=[
            ('SCAN', 'Automated Scan'),
            ('MANUAL', 'Manual Classification'),
            ('PATTERN', 'Pattern Matching'),
            ('ML', 'Machine Learning'),
        ],
        default='SCAN'
    )
    confidence_score = models.FloatField(default=1.0)  # 0.0 to 1.0
    
    # Status and compliance
    is_compliant = models.BooleanField(default=False)
    compliance_notes = models.TextField(blank=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    sample_data = models.TextField(blank=True)  # Masked sample for reference
    record_count = models.IntegerField(default=0)
    metadata = JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['database_name', 'table_name', 'column_name']
        indexes = [
            models.Index(fields=['database_name', 'table_name']),
            models.Index(fields=['category', 'pii_type']),
            models.Index(fields=['is_compliant']),
        ]
    
    def __str__(self):
        return f"{self.database_name}.{self.table_name}.{self.column_name} ({self.pii_type})"
    
    def get_full_path(self):
        """Get full data path."""
        return f"{self.database_name}.{self.table_name}.{self.column_name}"
    
    def mark_verified(self):
        """Mark as verified with current timestamp."""
        self.last_verified = timezone.now()
        self.save()


class DataSubject(BaseModel):
    """Represents a data subject (individual whose data is processed)."""
    
    # Subject identification
    subject_id = models.CharField(max_length=100, unique=True)  # Internal ID
    external_id = models.CharField(max_length=100, null=True, blank=True)  # Customer ID, etc.
    
    # Subject information (may be encrypted)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    
    # Consent management
    consent_given = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)
    consent_version = models.CharField(max_length=20, null=True, blank=True)
    consent_source = models.CharField(max_length=100, null=True, blank=True)
    
    # Rights exercised
    has_requested_access = models.BooleanField(default=False)
    has_requested_deletion = models.BooleanField(default=False)
    has_requested_portability = models.BooleanField(default=False)
    has_objected_processing = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    deletion_requested = models.BooleanField(default=False)
    deletion_scheduled = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    data_sources = JSONField(default=list, blank=True)  # List of systems containing data
    processing_purposes = JSONField(default=list, blank=True)
    legal_basis = JSONField(default=dict, blank=True)
    metadata = JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['subject_id']),
            models.Index(fields=['email']),
            models.Index(fields=['consent_given']),
            models.Index(fields=['deletion_requested']),
        ]
    
    def __str__(self):
        return f"Subject {self.subject_id} ({self.email or 'no email'})"
    
    def give_consent(self, version: str, source: str = 'web'):
        """Record consent given."""
        self.consent_given = True
        self.consent_date = timezone.now()
        self.consent_version = version
        self.consent_source = source
        self.save()
    
    def withdraw_consent(self):
        """Record consent withdrawal."""
        self.consent_given = False
        self.save()
    
    def request_deletion(self, scheduled_date: datetime = None):
        """Request data deletion."""
        self.deletion_requested = True
        self.deletion_scheduled = scheduled_date or (timezone.now() + timedelta(days=30))
        self.save()


class DataSubjectRequest(BaseModel):
    """Tracks data subject rights requests (GDPR Article 15-22)."""
    
    REQUEST_TYPES = [
        ('ACCESS', 'Right to Access (Art. 15)'),
        ('RECTIFICATION', 'Right to Rectification (Art. 16)'),
        ('ERASURE', 'Right to Erasure (Art. 17)'),
        ('RESTRICT', 'Right to Restrict Processing (Art. 18)'),
        ('PORTABILITY', 'Right to Data Portability (Art. 20)'),
        ('OBJECT', 'Right to Object (Art. 21)'),
    ]
    
    STATUS_CHOICES = [
        ('RECEIVED', 'Request Received'),
        ('VERIFIED', 'Identity Verified'),
        ('PROCESSING', 'Processing Request'),
        ('FULFILLED', 'Request Fulfilled'),
        ('REJECTED', 'Request Rejected'),
        ('PARTIALLY_FULFILLED', 'Partially Fulfilled'),
    ]
    
    # Request identification
    request_id = models.CharField(max_length=100, unique=True)
    subject = models.ForeignKey(DataSubject, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    
    # Request details
    description = models.TextField(blank=True)
    specific_data_requested = JSONField(default=list, blank=True)
    
    # Processing information
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RECEIVED')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(
        max_length=10,
        choices=[
            ('LOW', 'Low'),
            ('NORMAL', 'Normal'),
            ('HIGH', 'High'),
            ('URGENT', 'Urgent'),
        ],
        default='NORMAL'
    )
    
    # Timestamps
    received_date = models.DateTimeField(auto_now_add=True)
    verified_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField()  # Legal requirement: 1 month
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Response information
    response_data = JSONField(default=dict, blank=True)
    response_files = JSONField(default=list, blank=True)  # File paths
    rejection_reason = models.TextField(blank=True)
    
    # Audit trail
    processing_notes = models.TextField(blank=True)
    metadata = JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['request_id']),
            models.Index(fields=['subject', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['request_type', 'status']),
        ]
        ordering = ['-received_date']
    
    def __str__(self):
        return f"{self.request_id}: {self.get_request_type_display()} for {self.subject.subject_id}"
    
    def save(self, *args, **kwargs):
        # Set due date if not set (30 days from received date)
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=30)
        
        # Generate request ID if not set
        if not self.request_id:
            from django.utils.crypto import get_random_string
            self.request_id = f"DSR-{get_random_string(8).upper()}"
        
        super().save(*args, **kwargs)
    
    def is_overdue(self):
        """Check if request is overdue."""
        return self.status not in ['FULFILLED', 'REJECTED'] and timezone.now() > self.due_date
    
    def days_until_due(self):
        """Get days until due date."""
        if self.status in ['FULFILLED', 'REJECTED']:
            return 0
        
        delta = self.due_date - timezone.now()
        return max(0, delta.days)
    
    def mark_verified(self, verified_by: User):
        """Mark identity as verified."""
        self.status = 'VERIFIED'
        self.verified_date = timezone.now()
        self.assigned_to = verified_by
        self.save()
    
    def fulfill_request(self, response_data: Dict[str, Any], response_files: List[str] = None):
        """Mark request as fulfilled."""
        self.status = 'FULFILLED'
        self.completed_date = timezone.now()
        self.response_data = response_data
        self.response_files = response_files or []
        self.save()


class ConsentRecord(BaseModel):
    """Records consent given by data subjects."""
    
    subject = models.ForeignKey(DataSubject, on_delete=models.CASCADE)
    
    # Consent details
    purpose = models.CharField(max_length=200)  # Marketing, Analytics, etc.
    legal_basis = models.CharField(
        max_length=20,
        choices=[
            ('CONSENT', 'Consent (Art. 6.1.a)'),
            ('CONTRACT', 'Contract (Art. 6.1.b)'),
            ('LEGAL', 'Legal Obligation (Art. 6.1.c)'),
            ('VITAL', 'Vital Interests (Art. 6.1.d)'),
            ('PUBLIC', 'Public Task (Art. 6.1.e)'),
            ('LEGITIMATE', 'Legitimate Interest (Art. 6.1.f)'),
        ],
        default='CONSENT'
    )
    
    # Consent state
    is_active = models.BooleanField(default=True)
    consent_text = models.TextField()  # The actual consent text shown
    consent_version = models.CharField(max_length=20)
    
    # Timestamps
    given_date = models.DateTimeField(auto_now_add=True)
    withdrawn_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Context
    source = models.CharField(max_length=100)  # web, mobile, api, etc.
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Metadata
    metadata = JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['subject', 'purpose']),
            models.Index(fields=['is_active']),
            models.Index(fields=['given_date']),
        ]
        unique_together = ['subject', 'purpose', 'consent_version']
    
    def __str__(self):
        return f"Consent: {self.subject.subject_id} - {self.purpose} ({self.consent_version})"
    
    def withdraw(self):
        """Withdraw consent."""
        self.is_active = False
        self.withdrawn_date = timezone.now()
        self.save()
    
    def is_expired(self):
        """Check if consent is expired."""
        return self.expiry_date and timezone.now() > self.expiry_date


class PIIProcessingRecord(BaseModel):
    """Records PII processing activities for audit trail."""
    
    PROCESSING_TYPES = [
        ('COLLECTION', 'Data Collection'),
        ('PROCESSING', 'Data Processing'),
        ('STORAGE', 'Data Storage'),
        ('TRANSMISSION', 'Data Transmission'),
        ('ANALYSIS', 'Data Analysis'),
        ('DELETION', 'Data Deletion'),
        ('ANONYMIZATION', 'Data Anonymization'),
        ('PSEUDONYMIZATION', 'Data Pseudonymization'),
    ]
    
    # Processing details
    subject = models.ForeignKey(DataSubject, on_delete=models.CASCADE, null=True, blank=True)
    processing_type = models.CharField(max_length=20, choices=PROCESSING_TYPES)
    purpose = models.CharField(max_length=200)
    legal_basis = models.CharField(max_length=100)
    
    # Data details
    data_categories = JSONField(default=list, blank=True)  # Types of data processed
    data_sources = JSONField(default=list, blank=True)  # Where data came from
    data_recipients = JSONField(default=list, blank=True)  # Who data was shared with
    
    # Technical details
    system = models.CharField(max_length=100)  # System that performed processing
    processor = models.CharField(max_length=100)  # Component/service
    
    # Audit information
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True)
    
    # Compliance
    is_compliant = models.BooleanField(default=True)
    compliance_notes = models.TextField(blank=True)
    
    # Metadata
    metadata = JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['subject', 'processing_type']),
            models.Index(fields=['performed_at']),
            models.Index(fields=['system', 'processor']),
        ]
        ordering = ['-performed_at']
    
    def __str__(self):
        subject_str = self.subject.subject_id if self.subject else 'Unknown'
        return f"{self.get_processing_type_display()}: {subject_str} - {self.purpose}"


class RetentionPolicy(BaseModel):
    """Data retention policies for different data categories."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    # Policy details
    category = models.ForeignKey(PIICategory, on_delete=models.CASCADE)
    retention_period_days = models.IntegerField()
    
    # Actions after retention period
    action_after_retention = models.CharField(
        max_length=20,
        choices=[
            ('DELETE', 'Delete Data'),
            ('ANONYMIZE', 'Anonymize Data'),
            ('ARCHIVE', 'Archive Data'),
            ('REVIEW', 'Manual Review Required'),
        ],
        default='DELETE'
    )
    
    # Exceptions
    legal_hold_override = models.BooleanField(default=False)
    regulatory_requirements = JSONField(default=list, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    metadata = JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name_plural = "Retention Policies"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.retention_period_days} days"
    
    def calculate_expiry_date(self, created_date: datetime = None):
        """Calculate when data should expire based on this policy."""
        base_date = created_date or timezone.now()
        return base_date + timedelta(days=self.retention_period_days)