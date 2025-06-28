# app/core/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "transaction_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.services.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=60,
    task_time_limit=1800,  # 30 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        "process-due-future-transactions": {
            "task": "app.services.tasks.process_due_future_transactions_task",
            "schedule": 60.0,
        },
        "send-future-transaction-notifications": {
            "task": "app.services.tasks.send_future_transaction_notifications_task",
            "schedule": 3600.0,
        },
        "update-balance-cache": {
            "task": "app.services.tasks.update_balance_cache_task",
            "schedule": 300.0,
        },
    },
    task_routes={
        "app.services.tasks.process_transaction_task": {"queue": "transactions"},
        "app.services.tasks.update_balance_task": {"queue": "balances"},
        "app.services.tasks.send_notification_task": {"queue": "notifications"},
        "app.services.tasks.process_due_future_transactions_task": {
            "queue": "scheduled"
        },
    },
)
