# app/services/tasks.py

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import List
from celery import Task
from httpx import AsyncClient

from app.core.celery_app import celery_app
from app.db.session import db_manager
from app.db.repository import (
    FutureTransactionRepository,
    TransactionRepository,
    AccountRepository,
)
from app.domain.enums import (
    FutureTransactionTrigger,
    FutureTransactionStatus,
    TransactionCategory,
)
from app.domain.schemas import TransactionCreate
from app.events.publisher import event_publisher
from app.events.events import FutureTransactionTriggeredEvent
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AsyncTask(Task):
    def __call__(self, *args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.run_async(*args, **kwargs))
        finally:
            loop.close()


@celery_app.task(bind=True, base=AsyncTask, name="process_due_future_transactions")
async def process_due_future(self):
    async with db_manager.get_session() as session:
        future_repo = FutureTransactionRepository(session)
        txn_repo = TransactionRepository(session)
        acct_repo = AccountRepository(session)

        due = await future_repo.get_due(date.today())
        for fx in due:
            if fx.trigger_type != FutureTransactionTrigger.AUTOMATIC:
                continue
            tc = TransactionCreate(
                account_id=fx.account_id,
                amount=fx.amount,
                description=f"Auto: {fx.description}",
                category=fx.category,
            )
            txn = await txn_repo.create(tc, fx.created_by_user_id)

            acct = await acct_repo.get(fx.account_id)
            if acct:
                credit = fx.category == TransactionCategory.INCOME
                await acct_repo.adjust_balance(acct, fx.amount, credit)

            fx.status = FutureTransactionStatus.PROCESSED
            fx.triggered_date = fx.processed_date = datetime.utcnow()
            session.add(fx)
            await session.commit()

            await event_publisher.add_event(
                FutureTransactionTriggeredEvent(
                    future_transaction_id=fx.transaction_id,
                    transaction_id=txn.transaction_id,
                    account_id=fx.account_id,
                )
            )

        await event_publisher.publish_events()


@celery_app.task(bind=True, base=AsyncTask, name="send_future_notifications")
async def send_future_notifications(self):
    async with db_manager.get_session() as session:
        future_repo = FutureTransactionRepository(session)
        today = date.today()
        for offset in range(1, 31):
            check_date = today + timedelta(days=offset)
            due = await future_repo.get_due(check_date)
            for fx in due:
                if offset in fx.get_notification_days_list():
                    await celery_app.send_task(
                        "send_notification",
                        kwargs={
                            "user_ids": fx.get_notification_users_list(),
                            "subject": f"Future Due in {offset} days",
                            "message": f"TX {fx.transaction_id} due {fx.due_date}",
                            "transaction_id": fx.transaction_id,
                        },
                    )


@celery_app.task(bind=True, base=AsyncTask, name="send_notification")
async def send_notification(
    self, user_ids: List[int], subject: str, message: str, transaction_id: str = None
):
    try:
        async with AsyncClient() as client:
            r = await client.post(
                f"{settings.notification_service_url}/api/v1/notifications/send",
                json={
                    "user_ids": user_ids,
                    "subject": subject,
                    "message": message,
                    "transaction_id": transaction_id,
                },
                timeout=10.0,
            )
        if r.status_code != 200:
            logger.error("Notification failure: %s", r.text)
    except Exception as e:
        logger.error("Notification exception: %s", e)
        raise self.retry(exc=e, countdown=120, max_retries=3)


@celery_app.task(bind=True, base=AsyncTask, name="update_balance_cache")
async def update_balance_cache(self):
    async with db_manager.get_session() as session:
        from app.services.balances import BalanceService

        balance_service = BalanceService(session)
        await balance_service.get_all_balances()
