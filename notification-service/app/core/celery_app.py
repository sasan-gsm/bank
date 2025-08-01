from celery import Celery
from .config import settings

# Import JWT functionality from security module
from .security import (
    TokenData,
    JWTHandler,
    get_current_user,
    get_current_active_user,
    get_admin_user,
    require_permissions,
    jwt_handler
)

# Celery configuration
celery_app = Celery(
    "notification-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"]
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
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
