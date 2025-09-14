"""
Advanced audit logging utilities with immutable trails, SIEM integration,
and comprehensive security event tracking.
"""

import json
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from django.conf import settings
from django.db import transaction, connection
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
import threading
from queue import Queue
import requests
from dataclasses import dataclass
import logging

from security.models import AuditLog


logger = logging.getLogger(__name__)

# Thread-local storage for audit context
_audit_context = threading.local()


@dataclass
class AuditEvent:
    """Represents a security audit event."""
    action: str
    severity: str
    resource_type: str
    resource_id: Optional[str] = None
    description: str = ""
    success: bool = True
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


class AuditContext:
    """Context manager for audit operations."""
    
    def __init__(self, correlation_id: str = None, request: HttpRequest = None):
        self.correlation_id = correlation_id or self._generate_correlation_id()
        self.request = request
        self.events = []
    
    def __enter__(self):
        _audit_context.current = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(_audit_context, 'current'):
            delattr(_audit_context, 'current')
        
        # Flush any buffered events
        self._flush_events()
    
    def add_event(self, event: AuditEvent):
        """Add event to the current context."""
        if not event.correlation_id:
            event.correlation_id = self.correlation_id
        
        if self.request and not event.user_id:
            if hasattr(self.request, 'user') and self.request.user.is_authenticated:
                event.user_id = self.request.user.id
        
        if self.request and not event.ip_address:
            event.ip_address = self._get_client_ip(self.request)
        
        if self.request and not event.user_agent:
            event.user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        
        self.events.append(event)
    
    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _flush_events(self):
        """Flush all events in the context."""
        for event in self.events:
            AuditLogger.log_event(event)
        self.events.clear()


def get_current_audit_context() -> Optional[AuditContext]:
    """Get current audit context."""
    return getattr(_audit_context, 'current', None)


class AuditLogger:
    """Main audit logging utility with immutable trails."""
    
    # Event queue for async processing
    _event_queue = Queue()
    _background_thread = None
    _shutdown = False
    
    # SIEM integration settings
    SIEM_ENABLED = getattr(settings, 'SIEM_ENABLED', False)
    SIEM_ENDPOINT = getattr(settings, 'SIEM_ENDPOINT', '')
    SIEM_API_KEY = getattr(settings, 'SIEM_API_KEY', '')
    
    # Audit integrity settings
    INTEGRITY_KEY = getattr(settings, 'AUDIT_INTEGRITY_KEY', settings.SECRET_KEY)
    
    @classmethod
    def start_background_processor(cls):
        """Start background event processor."""
        if cls._background_thread is None or not cls._background_thread.is_alive():
            cls._shutdown = False
            cls._background_thread = threading.Thread(target=cls._process_events, daemon=True)
            cls._background_thread.start()
    
    @classmethod
    def shutdown(cls):
        """Shutdown background processor."""
        cls._shutdown = True
        if cls._background_thread and cls._background_thread.is_alive():
            cls._background_thread.join(timeout=5)
    
    @classmethod
    def _process_events(cls):
        """Background event processor."""
        while not cls._shutdown:
            try:
                # Process events from queue with timeout
                try:
                    event = cls._event_queue.get(timeout=1)
                    cls._store_audit_event(event)
                    cls._event_queue.task_done()
                except:
                    continue  # Timeout or queue empty
            except Exception as e:
                logger.error(f"Audit event processing error: {e}")
                time.sleep(1)
    
    @classmethod
    def log_event(cls, event: AuditEvent, async_mode: bool = True):
        """Log an audit event."""
        
        # Set timestamp if not provided
        if not event.timestamp:
            event.timestamp = timezone.now()
        
        if async_mode:
            # Ensure background processor is running
            cls.start_background_processor()
            
            # Add to queue for async processing
            cls._event_queue.put(event)
        else:
            # Synchronous processing
            cls._store_audit_event(event)
    
    @classmethod
    def _store_audit_event(cls, event: AuditEvent):
        """Store audit event with integrity protection."""
        
        try:
            with transaction.atomic():
                # Create audit log record
                audit_log = AuditLog.objects.create(
                    action=event.action,
                    severity=event.severity,
                    resource_type=event.resource_type,
                    resource_id=event.resource_id or '',
                    description=event.description,
                    success=event.success,
                    user_id=event.user_id,
                    session_id=event.session_id or '',
                    ip_address=event.ip_address or '',
                    user_agent=event.user_agent or '',
                    request_id=event.request_id or '',
                    correlation_id=event.correlation_id or '',
                    metadata=event.metadata or {},
                    timestamp=event.timestamp or timezone.now()
                )
                
                # Generate integrity hash
                integrity_hash = cls._generate_integrity_hash(audit_log)
                audit_log.integrity_hash = integrity_hash
                audit_log.save()
                
                # Send to SIEM if enabled
                if cls.SIEM_ENABLED:
                    cls._send_to_siem(audit_log)
                
                # Check for security alerts
                cls._check_security_alerts(audit_log)
                
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")
            # Try to store error event
            try:
                AuditLog.objects.create(
                    action='AUDIT_ERROR',
                    severity='HIGH',
                    resource_type='audit',
                    description=f'Failed to store audit event: {str(e)}',
                    success=False,
                    metadata={'original_event': event.__dict__, 'error': str(e)}
                )
            except:
                pass  # Last resort - log to file
                logger.critical(f"Critical audit failure: {e}")
    
    @classmethod
    def _generate_integrity_hash(cls, audit_log: AuditLog) -> str:
        """Generate integrity hash for audit log."""
        
        # Create hash payload
        payload = {
            'id': audit_log.id,
            'action': audit_log.action,
            'severity': audit_log.severity,
            'resource_type': audit_log.resource_type,
            'resource_id': audit_log.resource_id,
            'description': audit_log.description,
            'success': audit_log.success,
            'user_id': audit_log.user_id,
            'timestamp': audit_log.timestamp.isoformat(),
            'metadata': json.dumps(audit_log.metadata, sort_keys=True)
        }
        
        payload_str = json.dumps(payload, sort_keys=True)
        
        # Generate HMAC
        return hmac.new(
            cls.INTEGRITY_KEY.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @classmethod
    def verify_integrity(cls, audit_log: AuditLog) -> bool:
        """Verify audit log integrity."""
        if not audit_log.integrity_hash:
            return False
        
        expected_hash = cls._generate_integrity_hash(audit_log)
        return hmac.compare_digest(audit_log.integrity_hash, expected_hash)
    
    @classmethod
    def _send_to_siem(cls, audit_log: AuditLog):
        """Send audit event to SIEM system."""
        if not cls.SIEM_ENDPOINT or not cls.SIEM_API_KEY:
            return
        
        try:
            # Format for SIEM
            siem_event = {
                'timestamp': audit_log.timestamp.isoformat(),
                'event_id': str(audit_log.id),
                'source': 'bi-platform',
                'action': audit_log.action,
                'severity': audit_log.severity,
                'resource_type': audit_log.resource_type,
                'resource_id': audit_log.resource_id,
                'description': audit_log.description,
                'success': audit_log.success,
                'user_id': audit_log.user_id,
                'ip_address': audit_log.ip_address,
                'correlation_id': audit_log.correlation_id,
                'metadata': audit_log.metadata
            }
            
            # Send to SIEM
            headers = {
                'Authorization': f'Bearer {cls.SIEM_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                cls.SIEM_ENDPOINT,
                json=siem_event,
                headers=headers,
                timeout=5
            )
            
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to send event to SIEM: {e}")
    
    @classmethod
    def _check_security_alerts(cls, audit_log: AuditLog):
        """Check if audit event should trigger security alerts."""
        
        # High severity events
        if audit_log.severity == 'CRITICAL':
            cls._trigger_alert('CRITICAL_SECURITY_EVENT', audit_log)
        
        # Failed authentication attempts
        if audit_log.action in ['LOGIN_FAILED', 'MFA_FAILED'] and audit_log.ip_address:
            cls._check_brute_force(audit_log)
        
        # Data access violations
        if audit_log.action in ['PII_ACCESS', 'UNAUTHORIZED_ACCESS'] and not audit_log.success:
            cls._trigger_alert('DATA_ACCESS_VIOLATION', audit_log)
        
        # System integrity violations
        if audit_log.action in ['AUDIT_TAMPERING', 'SECURITY_CONFIG_CHANGED']:
            cls._trigger_alert('SYSTEM_INTEGRITY_VIOLATION', audit_log)
    
    @classmethod
    def _check_brute_force(cls, audit_log: AuditLog):
        """Check for brute force attacks."""
        if not audit_log.ip_address:
            return
        
        # Count failed attempts in last 15 minutes
        cutoff_time = timezone.now() - timedelta(minutes=15)
        
        failed_attempts = AuditLog.objects.filter(
            action__in=['LOGIN_FAILED', 'MFA_FAILED'],
            ip_address=audit_log.ip_address,
            timestamp__gte=cutoff_time,
            success=False
        ).count()
        
        if failed_attempts >= 5:  # Threshold for brute force
            cls._trigger_alert('BRUTE_FORCE_DETECTED', audit_log, {
                'failed_attempts': failed_attempts,
                'time_window': '15_minutes'
            })
    
    @classmethod
    def _trigger_alert(cls, alert_type: str, audit_log: AuditLog, extra_data: Dict[str, Any] = None):
        """Trigger security alert."""
        
        alert_data = {
            'alert_type': alert_type,
            'triggered_by': audit_log.id,
            'timestamp': timezone.now().isoformat(),
            'ip_address': audit_log.ip_address,
            'user_id': audit_log.user_id,
            'resource_type': audit_log.resource_type,
            'resource_id': audit_log.resource_id,
        }
        
        if extra_data:
            alert_data.update(extra_data)
        
        # Log the alert itself
        cls.log_event(AuditEvent(
            action='SECURITY_ALERT',
            severity='HIGH',
            resource_type='security',
            resource_id=alert_type,
            description=f'Security alert triggered: {alert_type}',
            success=True,
            metadata=alert_data
        ), async_mode=False)  # Synchronous to avoid recursion
    
    @classmethod
    def search_events(cls, filters: Dict[str, Any], limit: int = 100) -> List[AuditLog]:
        """Search audit events with filters."""
        
        queryset = AuditLog.objects.all()
        
        # Apply filters
        if 'action' in filters:
            queryset = queryset.filter(action=filters['action'])
        
        if 'severity' in filters:
            queryset = queryset.filter(severity=filters['severity'])
        
        if 'resource_type' in filters:
            queryset = queryset.filter(resource_type=filters['resource_type'])
        
        if 'user_id' in filters:
            queryset = queryset.filter(user_id=filters['user_id'])
        
        if 'ip_address' in filters:
            queryset = queryset.filter(ip_address=filters['ip_address'])
        
        if 'success' in filters:
            queryset = queryset.filter(success=filters['success'])
        
        if 'start_date' in filters:
            queryset = queryset.filter(timestamp__gte=filters['start_date'])
        
        if 'end_date' in filters:
            queryset = queryset.filter(timestamp__lte=filters['end_date'])
        
        if 'correlation_id' in filters:
            queryset = queryset.filter(correlation_id=filters['correlation_id'])
        
        return list(queryset.order_by('-timestamp')[:limit])
    
    @classmethod
    def get_audit_summary(cls, days: int = 7) -> Dict[str, Any]:
        """Get audit summary for the specified number of days."""
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Get raw SQL for better performance
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    action,
                    severity,
                    success,
                    COUNT(*) as count
                FROM security_auditlog 
                WHERE timestamp >= %s
                GROUP BY action, severity, success
                ORDER BY count DESC
            """, [start_date])
            
            rows = cursor.fetchall()
        
        # Process results
        summary = {
            'period': f'last_{days}_days',
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
            'total_events': sum(row[3] for row in rows),
            'by_action': {},
            'by_severity': {},
            'success_rate': 0
        }
        
        total_success = 0
        total_events = 0
        
        for action, severity, success, count in rows:
            # By action
            if action not in summary['by_action']:
                summary['by_action'][action] = {'total': 0, 'success': 0, 'failed': 0}
            
            summary['by_action'][action]['total'] += count
            if success:
                summary['by_action'][action]['success'] += count
                total_success += count
            else:
                summary['by_action'][action]['failed'] += count
            
            # By severity
            if severity not in summary['by_severity']:
                summary['by_severity'][severity] = 0
            summary['by_severity'][severity] += count
            
            total_events += count
        
        # Calculate success rate
        if total_events > 0:
            summary['success_rate'] = round((total_success / total_events) * 100, 2)
        
        return summary


# Decorators for audit logging
def audit_action(action: str, resource_type: str, severity: str = 'MEDIUM'):
    """Decorator to automatically audit function calls."""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                # Log the audit event
                duration = time.time() - start_time
                
                event = AuditEvent(
                    action=action,
                    severity=severity if success else 'HIGH',
                    resource_type=resource_type,
                    description=f'{func.__name__} {"completed" if success else "failed"}',
                    success=success,
                    metadata={
                        'function': func.__name__,
                        'duration_seconds': round(duration, 3),
                        'error': error
                    }
                )
                
                # Add to current context if available
                context = get_current_audit_context()
                if context:
                    context.add_event(event)
                else:
                    AuditLogger.log_event(event)
        
        return wrapper
    return decorator


def audit_model_changes(sender, **kwargs):
    """Signal handler to audit model changes."""
    
    instance = kwargs['instance']
    
    # Skip audit log models to avoid recursion
    if isinstance(instance, AuditLog):
        return
    
    # Determine action
    if kwargs.get('created'):
        action = 'MODEL_CREATED'
    else:
        action = 'MODEL_UPDATED'
    
    # Get user from current context or request
    user_id = None
    context = get_current_audit_context()
    if context and context.request and hasattr(context.request, 'user'):
        if context.request.user.is_authenticated:
            user_id = context.request.user.id
    
    event = AuditEvent(
        action=action,
        severity='LOW',
        resource_type=sender._meta.label_lower,
        resource_id=str(instance.pk) if instance.pk else None,
        description=f'{sender._meta.verbose_name} {action.lower()}',
        success=True,
        user_id=user_id,
        metadata={
            'model': sender._meta.label,
            'pk': str(instance.pk) if instance.pk else None,
        }
    )
    
    AuditLogger.log_event(event)


def audit_model_deletions(sender, **kwargs):
    """Signal handler to audit model deletions."""
    
    instance = kwargs['instance']
    
    # Skip audit log models
    if isinstance(instance, AuditLog):
        return
    
    # Get user from current context
    user_id = None
    context = get_current_audit_context()
    if context and context.request and hasattr(context.request, 'user'):
        if context.request.user.is_authenticated:
            user_id = context.request.user.id
    
    event = AuditEvent(
        action='MODEL_DELETED',
        severity='MEDIUM',
        resource_type=sender._meta.label_lower,
        resource_id=str(instance.pk),
        description=f'{sender._meta.verbose_name} deleted',
        success=True,
        user_id=user_id,
        metadata={
            'model': sender._meta.label,
            'pk': str(instance.pk),
        }
    )
    
    AuditLogger.log_event(event)


# Connect signals for automatic model audit
# Note: This should be configured in your Django app's apps.py
def connect_audit_signals():
    """Connect audit signals to all models."""
    post_save.connect(audit_model_changes)
    pre_delete.connect(audit_model_deletions)


# Context managers and utilities
class SecurityAuditContext(AuditContext):
    """Specialized context for security operations."""
    
    def __init__(self, operation: str, resource_type: str, resource_id: str = None, **kwargs):
        super().__init__(**kwargs)
        self.operation = operation
        self.resource_type = resource_type
        self.resource_id = resource_id
    
    def __enter__(self):
        super().__enter__()
        
        # Log operation start
        self.add_event(AuditEvent(
            action=f'{self.operation}_STARTED',
            severity='LOW',
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            description=f'Security operation {self.operation} started',
            success=True
        ))
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Log operation end
        success = exc_type is None
        
        self.add_event(AuditEvent(
            action=f'{self.operation}_COMPLETED' if success else f'{self.operation}_FAILED',
            severity='LOW' if success else 'HIGH',
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            description=f'Security operation {self.operation} {"completed" if success else "failed"}',
            success=success,
            metadata={'error': str(exc_val) if exc_val else None}
        ))
        
        super().__exit__(exc_type, exc_val, exc_tb)


# Shortcut functions for common audit events
def log_authentication_event(user_id: int, action: str, success: bool, 
                            ip_address: str = None, details: Dict[str, Any] = None):
    """Log authentication-related events."""
    
    event = AuditEvent(
        action=action,
        severity='MEDIUM' if success else 'HIGH',
        resource_type='authentication',
        resource_id=str(user_id) if user_id else None,
        description=f'Authentication event: {action}',
        success=success,
        user_id=user_id,
        ip_address=ip_address,
        metadata=details or {}
    )
    
    AuditLogger.log_event(event)


def log_data_access_event(resource_type: str, resource_id: str, action: str,
                         user_id: int = None, success: bool = True,
                         sensitive: bool = False, details: Dict[str, Any] = None):
    """Log data access events."""
    
    severity = 'HIGH' if sensitive else 'MEDIUM'
    if not success:
        severity = 'CRITICAL'
    
    event = AuditEvent(
        action=action,
        severity=severity,
        resource_type=resource_type,
        resource_id=resource_id,
        description=f'Data access: {action} on {resource_type}',
        success=success,
        user_id=user_id,
        metadata=details or {}
    )
    
    AuditLogger.log_event(event)


def log_security_config_change(config_type: str, change_details: Dict[str, Any],
                              user_id: int = None):
    """Log security configuration changes."""
    
    event = AuditEvent(
        action='SECURITY_CONFIG_CHANGED',
        severity='HIGH',
        resource_type='security_config',
        resource_id=config_type,
        description=f'Security configuration changed: {config_type}',
        success=True,
        user_id=user_id,
        metadata=change_details
    )
    
    AuditLogger.log_event(event)