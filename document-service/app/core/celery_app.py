# app/core/celery_app.py

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "document_service",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.services.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)
