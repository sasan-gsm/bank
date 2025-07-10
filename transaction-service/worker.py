import asyncio
from app.core.celery_app import celery_app

# Import tasks for registration
from app.services.tasks import (
    process_due_future,
    send_future_notifications,
    send_notification,
    update_balance_cache,
)

if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main():
    celery_app.start(
        argv=[
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--queues=transactions,balances,notifications,scheduled,default",
        ]
    )


if __name__ == "__main__":
    main()
