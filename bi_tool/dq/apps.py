"""
Data Quality Django app configuration.
"""

from django.apps import AppConfig


class DqConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dq'
    verbose_name = 'Data Quality'
    
    def ready(self):
        """Initialize DQ system when Django starts."""
        import dq.signals  # noqa