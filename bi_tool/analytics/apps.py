from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'Analytics & Business Data'
    
    def ready(self):
        """
        Import signals when the app is ready
        """
        import analytics.signals  # noqa