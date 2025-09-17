"""
Celery configuration for BI Tool
Handles asynchronous task processing for ETL and DQ operations.
"""

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Set default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bi_tool.settings')

# Create Celery instance
app = Celery('bi_tool')

# Configure Celery using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Task routing configuration
app.conf.task_routes = {
    'etl.tasks.*': {'queue': 'etl'},
    'dq.tasks.*': {'queue': 'dq'},
    'analytics.tasks.*': {'queue': 'analytics'},
}

# Celery Beat configuration for scheduled tasks
app.conf.beat_schedule = {
    'schedule-dq-checks': {
        'task': 'dq.tasks.schedule_dq_checks',
        'schedule': 60.0,  # Run every minute
    },
    'cleanup-old-dq-runs': {
        'task': 'dq.tasks.cleanup_old_dq_runs',
        'schedule': 86400.0,  # Run daily
    },
    'dq-health-check': {
        'task': 'dq.tasks.run_dq_health_check',
        'schedule': 300.0,  # Run every 5 minutes
    },
}

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')


# Task failure handling
@app.task(bind=True)
def handle_task_failure(self, task_id, error, traceback):
    """Handle task failures and send notifications."""
    print(f'Task {task_id} failed with error: {error}')
    # Add notification logic here if needed


# Celery signal handlers
from celery.signals import task_failure

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Handle task failures."""
    print(f'Task {task_id} failed: {exception}')
    # Log to monitoring system or send alerts