"""Celery worker entrypoint for background task processing."""

import asyncio
from celery.signals import worker_ready, worker_shutdown

from app.core.config import settings
from app.core.celery_app import celery_app
from app.streams.handlers import (
    send_email_task,
    process_user_created_event,
    process_user_updated_event,
    process_user_deleted_event,
    cleanup_expired_otps_task,
)
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set event loop policy for Windows compatibility
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handler called when worker is ready."""
    logger.info("Celery worker is ready and waiting for tasks")
    logger.info(f"Worker configuration: broker={settings.redis_url}")
    logger.info(f"Registered tasks: {list(celery_app.tasks.keys())}")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handler called when worker is shutting down."""
    logger.info("Celery worker is shutting down")


def main():
    """Main function to start the Celery worker."""
    logger.info("Starting Celery worker for auth-service")

    # Start the worker
    celery_app.start(
        [
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--pool=threads",  # Use threads for async tasks
            "--queues=auth_service,email,events,cleanup",
            "--hostname=auth-worker@%h",
        ]
    )


if __name__ == "__main__":
    main()
