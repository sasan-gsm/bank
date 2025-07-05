"""
Celery configuration for background task processing.
Handles email sending, notifications, and inter-service communication.
"""

from celery import Celery
from .config import settings

# Create Celery instance
celery_app = Celery(
    "auth-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.streams.handlers"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=60,  # 1 minute
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    "app.streams.handlers.send_email_task": {"queue": "email"},
    "app.streams.handlers.send_otp_task": {"queue": "otp"},
    "app.streams.handlers.notify_user_created_task": {"queue": "notifications"},
}
