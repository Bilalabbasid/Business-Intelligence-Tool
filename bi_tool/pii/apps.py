"""
PII app configuration.
"""

from django.apps import AppConfig


class PiiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pii'
    verbose_name = 'PII Protection & GDPR Compliance'