# This file makes Python treat the directory as a package

from __future__ import absolute_import, unicode_literals

# Import Celery app to ensure it's loaded when Django starts
from .celery import app as celery_app

__all__ = ('celery_app',)