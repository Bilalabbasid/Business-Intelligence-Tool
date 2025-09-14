from django.apps import AppConfig


class EtlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'etl'
    verbose_name = 'ETL (Extract, Transform, Load)'

    def ready(self):
        """Import signal handlers when app is ready."""
        import etl.signals  # noqa