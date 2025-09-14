"""
Security app configuration for BI Tool.
"""

from django.apps import AppConfig


class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'security'
    verbose_name = 'Security, Compliance & Data Privacy'
    
    def ready(self):
        """Initialize security components when Django starts."""
        try:
            # Import and connect audit signals
            from .audit import connect_audit_signals
            connect_audit_signals()
            
            # Start background audit processor
            from .audit import AuditLogger
            AuditLogger.start_background_processor()
            
        except Exception as e:
            # Don't fail Django startup if security components have issues
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Security app initialization warning: {e}")