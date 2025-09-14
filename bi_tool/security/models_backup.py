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


class User(AbstractUser):
    """Extended user model with security features."""
    
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Administrator'),
        ('MANAGER', 'Manager'),
        ('ANALYST', 'Data Analyst'),
        ('STAFF', 'Staff User'),
        ('ETL_ADMIN', 'ETL Administrator'),
        ('SECURITY_ADMIN', 'Security Administrator'),
        ('VIEWER', 'Read-only Viewer'),
    ]
    
    BRANCH_CHOICES = [
        ('ALL', 'All Branches'),
        ('NORTH', 'North Region'),
        ('SOUTH', 'South Region'),
        ('EAST', 'East Region'),
        ('WEST', 'West Region'),
        ('CENTRAL', 'Central Office'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='VIEWER')
    branch_id = models.CharField(max_length=20, choices=BRANCH_CHOICES, default='ALL')
    allowed_branches = models.JSONField(default=list, blank=True)
    resource_scopes = models.JSONField(default=list, blank=True)
    
    # Security fields
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=32, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(default=timezone.now)
    password_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Compliance fields
    consent_marketing = models.BooleanField(default=False)
    consent_analytics = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)
    data_retention_expires = models.DateTimeField(null=True, blank=True)
    
    # Audit fields
    created_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_users')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'security_users'
        indexes = [
            models.Index(fields=['role', 'branch_id']),
            models.Index(fields=['account_locked_until']),
            models.Index(fields=['data_retention_expires']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_account_locked(self):
        """Check if account is currently locked."""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration."""
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])
    
    def unlock_account(self):
        """Unlock account and reset failed attempts."""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])
    
    def has_branch_access(self, branch_id):
        """Check if user has access to specific branch."""
        if self.branch_id == 'ALL':
            return True
        if self.branch_id == branch_id:
            return True
        return branch_id in self.allowed_branches
    
    def has_resource_scope(self, resource_type, action='read'):
        """Check if user has access to resource type and action."""
        for scope in self.resource_scopes:
            if scope.get('resource') == resource_type:
                return action in scope.get('actions', [])
        return False


class AuditLog(models.Model):
    """Immutable audit trail for security events."""
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('LOGIN_FAILED', 'Failed Login'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('MFA_ENABLED', 'MFA Enabled'),
        ('MFA_DISABLED', 'MFA Disabled'),
        ('USER_CREATED', 'User Created'),
        ('USER_UPDATED', 'User Updated'),
        ('USER_DELETED', 'User Deleted'),
        ('DATA_EXPORT', 'Data Export'),
        ('DATA_ACCESS', 'Data Access'),
        ('PII_ACCESS', 'PII Data Access'),
        ('ADMIN_ACTION', 'Administrative Action'),
        ('SECURITY_EVENT', 'Security Event'),
        ('DSAR_REQUEST', 'Data Subject Access Request'),
        ('DATA_DELETION', 'Data Deletion'),
        ('CONSENT_CHANGE', 'Consent Changed'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access Attempt'),
        ('ENCRYPTION_KEY_ROTATION', 'Encryption Key Rotation'),
        ('BACKUP_CREATED', 'Backup Created'),
        ('SYSTEM_CONFIG_CHANGE', 'System Configuration Change'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=64, unique=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # User context
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    user_id_snapshot = models.UUIDField(null=True, blank=True)  # Backup in case user is deleted
    username_snapshot = models.CharField(max_length=150, blank=True)
    role_snapshot = models.CharField(max_length=20, blank=True)
    
    # Action details
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM')
    resource_type = models.CharField(max_length=50, blank=True)
    resource_id = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    
    # Technical details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    session_id = models.CharField(max_length=64, blank=True)
    
    # Change tracking
    changes = models.JSONField(default=dict, blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    
    # Status and metadata
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Compliance fields
    retention_expires_at = models.DateTimeField(db_index=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'security_audit_logs'
        indexes = [
            models.Index(fields=['timestamp', 'action']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['severity', 'timestamp']),
            models.Index(fields=['retention_expires_at']),
        ]
        permissions = [
            ('view_audit_logs', 'Can view audit logs'),
            ('export_audit_logs', 'Can export audit logs'),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to ensure immutability and set defaults."""
        if self.pk is not None:
            raise ValueError("Audit logs are immutable and cannot be updated")
        
        # Generate unique event ID
        if not self.event_id:
            self.event_id = self.generate_event_id()
        
        # Set user snapshots
        if self.user:
            self.user_id_snapshot = self.user.id
            self.username_snapshot = self.user.username
            self.role_snapshot = self.user.role
        
        # Set retention period (7 years by default for compliance)
        if not self.retention_expires_at:
            self.retention_expires_at = timezone.now() + timedelta(days=7*365)
        
        super().save(*args, **kwargs)
    
    def generate_event_id(self):
        """Generate unique event ID."""
        timestamp = str(int(timezone.now().timestamp() * 1000000))
        unique_data = f"{timestamp}_{self.action}_{uuid.uuid4().hex[:8]}"
        return hashlib.sha256(unique_data.encode()).hexdigest()[:32]
    
    def __str__(self):
        return f"{self.timestamp.isoformat()} - {self.get_action_display()} by {self.username_snapshot}"


class SessionToken(models.Model):
    """Secure session token management."""
    
    TOKEN_TYPES = [
        ('ACCESS', 'Access Token'),
        ('REFRESH', 'Refresh Token'),
        ('MFA', 'MFA Token'),
        ('RESET', 'Password Reset Token'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    token_type = models.CharField(max_length=10, choices=TOKEN_TYPES)
    token_hash = models.CharField(max_length=64, unique=True)  # Store hash, not raw token
    
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'security_session_tokens'
        indexes = [
            models.Index(fields=['user', 'token_type', 'is_revoked']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
        ]
    
    def is_valid(self):
        """Check if token is valid and not expired."""
        if self.is_revoked:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def revoke(self, reason='Manual revocation'):
        """Revoke the token."""
        self.is_revoked = True
        self.revoked_at = timezone.now()
        self.revocation_reason = reason
        self.save(update_fields=['is_revoked', 'revoked_at', 'revocation_reason'])
    
    def update_last_used(self, ip_address=None):
        """Update last used timestamp and IP."""
        self.last_used_at = timezone.now()
        if ip_address:
            self.ip_address = ip_address
        self.save(update_fields=['last_used_at', 'ip_address'])
    
    @classmethod
    def create_token(cls, user, token_type, raw_token, expires_in_seconds, ip_address=None, user_agent=None):
        """Create new token with hash."""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = timezone.now() + timedelta(seconds=expires_in_seconds)
        
        return cls.objects.create(
            user=user,
            token_type=token_type,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    @classmethod
    def verify_token(cls, raw_token, token_type=None):
        """Verify token and return session if valid."""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        query = cls.objects.filter(token_hash=token_hash, is_revoked=False)
        if token_type:
            query = query.filter(token_type=token_type)
        
        try:
            session = query.get()
            if session.is_valid():
                return session
        except cls.DoesNotExist:
            pass
        
        return None


class EncryptionKey(models.Model):
    """Encryption key management for data protection."""
    
    KEY_TYPES = [
        ('MASTER', 'Master Key'),
        ('DATA', 'Data Encryption Key'),
        ('FIELD', 'Field-Level Encryption Key'),
        ('BACKUP', 'Backup Encryption Key'),
    ]
    
    ALGORITHMS = [
        ('AES-256-GCM', 'AES-256-GCM'),
        ('FERNET', 'Fernet (AES-128-CBC + HMAC-SHA256)'),
        ('RSA-2048', 'RSA-2048'),
        ('RSA-4096', 'RSA-4096'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key_id = models.CharField(max_length=64, unique=True)
    key_type = models.CharField(max_length=10, choices=KEY_TYPES)
    algorithm = models.CharField(max_length=20, choices=ALGORITHMS)
    
    # Key metadata
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    
    # Key status
    is_active = models.BooleanField(default=True)
    is_compromised = models.BooleanField(default=False)
    rotated_at = models.DateTimeField(null=True, blank=True)
    
    # External key management
    kms_key_id = models.CharField(max_length=255, blank=True)  # AWS KMS, Vault, etc.
    kms_provider = models.CharField(max_length=50, blank=True)
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    tags = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'security_encryption_keys'
        indexes = [
            models.Index(fields=['key_type', 'is_active']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ('rotate_encryption_keys', 'Can rotate encryption keys'),
            ('view_key_metadata', 'Can view key metadata'),
        ]
    
    def is_valid(self):
        """Check if key is valid and not expired."""
        if not self.is_active or self.is_compromised:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def mark_compromised(self, reason=''):
        """Mark key as compromised."""
        self.is_compromised = True
        self.is_active = False
        self.save(update_fields=['is_compromised', 'is_active'])
        
        # Log security event
        AuditLog.objects.create(
            action='SECURITY_EVENT',
            severity='CRITICAL',
            resource_type='encryption_key',
            resource_id=str(self.id),
            description=f'Encryption key {self.key_id} marked as compromised: {reason}',
            metadata={'key_type': self.key_type, 'algorithm': self.algorithm}
        )
    
    def rotate(self, new_kms_key_id=None):
        """Rotate the encryption key."""
        self.is_active = False
        self.rotated_at = timezone.now()
        self.save(update_fields=['is_active', 'rotated_at'])
        
        # Create new key version
        new_key = EncryptionKey.objects.create(
            key_id=self.key_id,
            key_type=self.key_type,
            algorithm=self.algorithm,
            version=self.version + 1,
            expires_at=timezone.now() + timedelta(days=365),
            kms_key_id=new_kms_key_id or self.kms_key_id,
            kms_provider=self.kms_provider,
            description=f'Rotated version of {self.key_id}',
            tags=self.tags,
        )
        
        # Log rotation event
        AuditLog.objects.create(
            action='ENCRYPTION_KEY_ROTATION',
            severity='HIGH',
            resource_type='encryption_key',
            resource_id=str(self.id),
            description=f'Encryption key {self.key_id} rotated from version {self.version} to {new_key.version}',
            metadata={
                'old_key_id': str(self.id),
                'new_key_id': str(new_key.id),
                'key_type': self.key_type,
            }
        )
        
        return new_key
    
    def increment_usage(self):
        """Increment usage counter."""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])
    
    def __str__(self):
        return f"{self.key_id} v{self.version} ({self.get_key_type_display()})"


class SecurityConfiguration(models.Model):
    """Security configuration settings."""
    
    CATEGORIES = [
        ('AUTH', 'Authentication'),
        ('RBAC', 'Role-Based Access Control'),
        ('ENCRYPTION', 'Encryption'),
        ('AUDIT', 'Audit Logging'),
        ('COMPLIANCE', 'Compliance'),
        ('MONITORING', 'Security Monitoring'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    key = models.CharField(max_length=100)
    value = models.TextField()
    value_type = models.CharField(max_length=20, default='string')  # string, int, bool, json
    
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'security_configuration'
        unique_together = ['category', 'key']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]
        permissions = [
            ('change_security_config', 'Can change security configuration'),
        ]
    
    def get_typed_value(self):
        """Return value with correct type."""
        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'json':
            return json.loads(self.value)
        return self.value
    
    def set_typed_value(self, value):
        """Set value with type detection."""
        if isinstance(value, bool):
            self.value_type = 'bool'
            self.value = str(value).lower()
        elif isinstance(value, int):
            self.value_type = 'int'
            self.value = str(value)
        elif isinstance(value, (dict, list)):
            self.value_type = 'json'
            self.value = json.dumps(value)
        else:
            self.value_type = 'string'
            self.value = str(value)
    
    def __str__(self):
        return f"{self.category}:{self.key} = {self.value if not self.is_sensitive else '***'}"