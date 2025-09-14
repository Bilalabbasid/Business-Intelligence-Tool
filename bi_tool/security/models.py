"""
Security models for audit logging, user management, and compliance.
"""

import uuid
import json
from datetime import datetime, timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone
import hashlib
import hmac
import os

from core.models import BaseModel

User = get_user_model()


class AuditLog(BaseModel):
    """Immutable audit log for all system activities."""
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Event identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=100, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM')
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    
    # User and session context
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Request context
    request_id = models.CharField(max_length=100, blank=True)
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Event details
    success = models.BooleanField(default=True)
    metadata = models.TextField(default='{}')  # JSON as text field
    
    # Audit integrity
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    integrity_hash = models.CharField(max_length=64, blank=True)
    
    class Meta:
        db_table = 'security_audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['severity', 'timestamp']),
            models.Index(fields=['success', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.timestamp} - {self.user}"
    
    def get_metadata(self):
        """Parse metadata JSON."""
        try:
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata(self, data):
        """Set metadata as JSON string."""
        self.metadata = json.dumps(data) if data else '{}'
    
    def save(self, *args, **kwargs):
        """Override save to prevent modifications after creation."""
        if self.pk is not None:
            # This is an update - prevent it
            raise ValueError("Audit logs are immutable and cannot be modified")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of audit logs."""
        raise ValueError("Audit logs are immutable and cannot be deleted")


class EncryptionKey(BaseModel):
    """Manage encryption keys with rotation and lifecycle."""
    
    KEY_TYPES = [
        ('SYMMETRIC', 'Symmetric Encryption'),
        ('ASYMMETRIC', 'Asymmetric Encryption'),
        ('SIGNING', 'Digital Signing'),
    ]
    
    ALGORITHMS = [
        ('AES-256-GCM', 'AES 256 GCM'),
        ('RSA-2048', 'RSA 2048'),
        ('RSA-4096', 'RSA 4096'),
        ('ECDSA-P256', 'ECDSA P-256'),
    ]
    
    # Key identification
    key_id = models.CharField(max_length=100, unique=True)
    key_type = models.CharField(max_length=20, choices=KEY_TYPES)
    algorithm = models.CharField(max_length=20, choices=ALGORITHMS)
    version = models.PositiveIntegerField(default=1)
    
    # Key management
    is_active = models.BooleanField(default=True)
    kms_key_id = models.CharField(max_length=200, blank=True)  # External KMS reference
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    metadata = models.TextField(default='{}')  # JSON as text field
    
    class Meta:
        db_table = 'security_encryption_keys'
        unique_together = [('key_id', 'version')]
        indexes = [
            models.Index(fields=['key_id', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.key_id} v{self.version} ({self.algorithm})"
    
    def get_metadata(self):
        """Parse metadata JSON."""
        try:
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata(self, data):
        """Set metadata as JSON string."""
        self.metadata = json.dumps(data) if data else '{}'
    
    def is_valid(self):
        """Check if key is valid (active and not expired)."""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])


class SessionToken(BaseModel):
    """Manage user session tokens for authentication."""
    
    TOKEN_TYPES = [
        ('ACCESS', 'Access Token'),
        ('REFRESH', 'Refresh Token'),
        ('API', 'API Token'),
    ]
    
    # Token identification
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    token_type = models.CharField(max_length=10, choices=TOKEN_TYPES)
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hash of token
    
    # Token lifecycle
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Context
    created_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.TextField(default='{}')  # JSON as text field
    
    class Meta:
        db_table = 'security_session_tokens'
        indexes = [
            models.Index(fields=['user', 'token_type', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_token_type_display()}"
    
    def get_metadata(self):
        """Parse metadata JSON."""
        try:
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata(self, data):
        """Set metadata as JSON string."""
        self.metadata = json.dumps(data) if data else '{}'
    
    def is_valid(self):
        """Check if token is valid (active and not expired)."""
        if not self.is_active:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def revoke(self):
        """Revoke the token."""
        self.is_active = False
        self.save(update_fields=['is_active'])


class SecurityConfiguration(BaseModel):
    """Store security configuration settings."""
    
    CONFIG_TYPES = [
        ('PASSWORD_POLICY', 'Password Policy'),
        ('SESSION', 'Session Management'),
        ('MFA', 'Multi-Factor Authentication'),
        ('RATE_LIMIT', 'Rate Limiting'),
        ('AUDIT', 'Audit Settings'),
        ('ENCRYPTION', 'Encryption Settings'),
    ]
    
    # Configuration identification
    config_key = models.CharField(max_length=100, unique=True)
    config_type = models.CharField(max_length=20, choices=CONFIG_TYPES)
    
    # Configuration data
    config_value = models.TextField()  # JSON configuration
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    metadata = models.TextField(default='{}')  # JSON as text field
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'security_configuration'
        indexes = [
            models.Index(fields=['config_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.config_key} ({self.get_config_type_display()})"
    
    def get_config_value(self):
        """Parse configuration value as JSON."""
        try:
            return json.loads(self.config_value)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_config_value(self, data):
        """Set configuration value as JSON string."""
        self.config_value = json.dumps(data) if data else '{}'
    
    def get_metadata(self):
        """Parse metadata JSON."""
        try:
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata(self, data):
        """Set metadata as JSON string."""
        self.metadata = json.dumps(data) if data else '{}'


class SecurityAlert(BaseModel):
    """Security alerts and notifications."""
    
    ALERT_TYPES = [
        ('BRUTE_FORCE', 'Brute Force Attack'),
        ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
        ('DATA_BREACH', 'Data Breach'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'),
        ('POLICY_VIOLATION', 'Policy Violation'),
        ('SYSTEM_COMPROMISE', 'System Compromise'),
    ]
    
    STATUSES = [
        ('OPEN', 'Open'),
        ('INVESTIGATING', 'Under Investigation'),
        ('RESOLVED', 'Resolved'),
        ('FALSE_POSITIVE', 'False Positive'),
    ]
    
    # Alert identification
    alert_id = models.CharField(max_length=100, unique=True)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=AuditLog.SEVERITY_CHOICES, default='MEDIUM')
    
    # Alert details
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUSES, default='OPEN')
    
    # Context
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    affected_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='security_alerts')
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=200, blank=True)
    
    # Management
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Metadata
    metadata = models.TextField(default='{}')  # JSON as text field
    
    class Meta:
        db_table = 'security_alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', 'status']),
            models.Index(fields=['severity', 'created_at']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"{self.alert_id}: {self.title}"
    
    def get_metadata(self):
        """Parse metadata JSON."""
        try:
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata(self, data):
        """Set metadata as JSON string."""
        self.metadata = json.dumps(data) if data else '{}'
    
    def resolve(self, resolved_by, notes=''):
        """Mark alert as resolved."""
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.assigned_to = resolved_by
        self.save()