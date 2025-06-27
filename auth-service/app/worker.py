"""
Celery worker application for background task processing.
Handles email sending, notifications, and inter-service communication.
"""

import asyncio
from celery import Celery
from app.core.config import settings
from app.core.celery_app import celery_app

# Import task modules to register them
from app.streams.handlers import (
    send_email_task,
    send_otp_task,
    notify_user_created_task,
    notify_user_updated_task,
    notify_user_deleted_task,
)

# Set event loop policy for Windows compatibility
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main():
    """
    Main function to start Celery worker.
    """
    celery_app.start(
        argv=[
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--queues=email,otp,notifications,default",
        ]
    )


if __name__ == "__main__":
    main()
