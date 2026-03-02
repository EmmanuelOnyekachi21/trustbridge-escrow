"""Celery application configuration.

This module sets up Celery for background task processing.
Celery handles:
    - Periodic tasks (beat schedule)
    - Async task execution
    - Task result storage

Architecture:
    - Broker: Redis (task queue)
    - Backend: Redis (result storage)
    - Worker: Separate process that executes tasks
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "trustbridge",
    broker=settings.redis_url,  # Where to queue tasks
    backend=settings.redis_url,  # Where to store results
    include=[
        "app.tasks.currency",  # Auto-discover tasks in this module
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",  # How to serialize task arguments
    accept_content=["json"],  # Only accept JSON (security)
    result_serializer="json",  # How to serialize task results
    timezone="UTC",  # All times in UTC
    enable_utc=True,  # Enable UTC timezone

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Task execution settings
    task_track_started=True,  # Track when task starts
    task_time_limit=300,  # Kill task after 5 minutes
    task_soft_time_limit=240,  # Warn task after 4 minutes

    # Worker settings
    worker_prefetch_multiplier=1,  # Take 1 task at a time (fair distribution)
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks

    # Beat schedule (periodic tasks)
    beat_schedule={
        # Refresh exchange rates every 1 hour
        "refresh_exchange_rates": {
            "task": "app.tasks.currency.refresh_exchange_rates",
            "schedule": crontab(minute=0, hour="*/1"),  # Every hour
        },
    },
)

# Configure logging
celery_app.conf.update(
    worker_log_format=(
        "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    ),
    worker_task_log_format=(
        "[%(asctime)s: %(levelname)s/%(processName)s] "
        "[%(task_name)s(%(task_id)s)] %(message)s"
    ),
)


@celery_app.task(name="app.tasks.health_check")
def health_check():
    """Simple task to verify Celery is working.

    Returns:
        Dictionary with status and message.
    """
    return {"status": "healthy", "message": "Celery is running"}

