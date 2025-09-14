from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = 'Business Intelligence API'
    
    def ready(self):
        """
        Import signals when the app is ready
        """
        pass  # No signals needed for API app