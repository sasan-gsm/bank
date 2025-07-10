from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination import Page
from app.db.repository import (
    FutureTransactionRepository,
    TransactionRepository,
    AccountRepository,
)
from app.domain.schemas import (
    FutureTransactionCreate,
    FutureTransactionUpdate,
    FutureTransactionResponse,
    TransactionCreate,
)
from app.domain.enums import (
    FutureTransactionStatus,
    TransactionCategory,
    TransactionStatus,
)
from app.core.exceptions import (
    NotFoundError,
    InvalidTransactionError,
    AlreadyProcessedError,
    InsufficientBalanceError,
)
from app.events.events import (
    FutureTransactionCreatedEvent,
    FutureTransactionTriggeredEvent,
    FutureTransactionCancelledEvent,
)
from app.events.publisher import event_publisher
from app.core.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


class FutureTransactionService:
    """Service for managing future transactions."""

    def __init__(self, session: AsyncSession):
        self.future_repo = FutureTransactionRepository(session)
        self.txn_repo = TransactionRepository(session)
        self.acct_repo = AccountRepository(session)
        self.session = session

    async def create_future_transaction(
        self, payload: FutureTransactionCreate, user_id: int
    ) -> FutureTransactionResponse:
        """Create a new future transaction with notification scheduling."""
        # Validate account exists
        account = await self.acct_repo.get(payload.account_id)
        if not account:
            raise NotFoundError(f"Account {payload.account_id} not found")

        # Validate due date is in the future
        if payload.due_date <= date.today():
            raise InvalidTransactionError("Due date must be in the future")

        # Create future transaction
        future_txn = await self.future_repo.create(payload, user_id)

        # Schedule notifications if specified
        if payload.notification_days and payload.notification_users:
            await self._schedule_notifications(future_txn)

        # Publish event
        await event_publisher.add_event(
            FutureTransactionCreatedEvent(
                future_transaction_id=future_txn.id,
                transaction_id=future_txn.transaction_id,
                account_id=future_txn.account_id,
                amount=float(future_txn.amount),
                due_date=future_txn.due_date.isoformat(),
                trigger_type=future_txn.trigger_type.value,
                user_id=user_id,
            )
        )

        return FutureTransactionResponse.model_validate(future_txn)

    async def get_future_transaction(
        self, transaction_id: str
    ) -> FutureTransactionResponse:
        """Get a future transaction by ID."""
        future_txn = await self.future_repo.get_by_transaction_id(transaction_id)
        if not future_txn:
            raise NotFoundError(f"Future transaction {transaction_id} not found")
        return FutureTransactionResponse.model_validate(future_txn)

    async def update_future_transaction(
        self, transaction_id: str, payload: FutureTransactionUpdate, user_id: int
    ) -> FutureTransactionResponse:
        """Update a future transaction."""
        future_txn = await self.future_repo.get_by_transaction_id(transaction_id)
        if not future_txn:
            raise NotFoundError(f"Future transaction {transaction_id} not found")

        if future_txn.status != FutureTransactionStatus.SCHEDULED:
            raise AlreadyProcessedError(
                "Cannot modify a processed or scrapped transaction"
            )

        # Update the transaction
        future_txn = await self.future_repo.update(future_txn, payload)

        # Reschedule notifications if they were updated
        if (
            payload.notification_days is not None
            or payload.notification_users is not None
        ):
            await self._schedule_notifications(future_txn)

        return FutureTransactionResponse.model_validate(future_txn)

    async def trigger_future_transaction(
        self, transaction_id: str, user_id: int
    ) -> FutureTransactionResponse:
        """Manually trigger a future transaction."""
        future_txn = await self.future_repo.get_by_transaction_id(transaction_id)
        if not future_txn:
            raise NotFoundError(f"Future transaction {transaction_id} not found")

        if future_txn.status != FutureTransactionStatus.SCHEDULED:
            raise AlreadyProcessedError("Transaction already processed or scrapped")

        # Check if account has sufficient balance for expenses
        account = await self.acct_repo.get(future_txn.account_id)
        if not account:
            raise NotFoundError(f"Account {future_txn.account_id} not found")

        if (
            future_txn.category == TransactionCategory.EXPENSE
            and account.available_balance < future_txn.amount
        ):
            raise InsufficientBalanceError("Insufficient funds to process transaction")

        # Create the actual transaction
        txn_create = TransactionCreate(
            account_id=future_txn.account_id,
            amount=future_txn.amount,
            description=f"Triggered: {future_txn.description}",
            category=future_txn.category,
            reference_number=future_txn.reference_number,
            notes=future_txn.notes,
        )

        actual_txn = await self.txn_repo.create(txn_create, user_id)

        # Adjust account balance
        credit = future_txn.category == TransactionCategory.INCOME
        await self.acct_repo.adjust_balance(account, future_txn.amount, credit)

        # Update future transaction status
        future_txn.status = FutureTransactionStatus.PROCESSED
        future_txn.triggered_date = datetime.utcnow()
        future_txn.processed_date = datetime.utcnow()
        future_txn.triggered_by_user_id = user_id
        await self.session.commit()

        # Set actual transaction as processed
        actual_txn.status = TransactionStatus.PROCESSED
        actual_txn.processed_date = datetime.utcnow()
        await self.session.commit()

        # Publish event
        await event_publisher.add_event(
            FutureTransactionTriggeredEvent(
                future_transaction_id=future_txn.id,
                transaction_id=actual_txn.transaction_id,
                account_id=future_txn.account_id,
                triggered_by_user_id=user_id,
            )
        )

        return FutureTransactionResponse.model_validate(future_txn)

    async def scrap_future_transaction(
        self, transaction_id: str, user_id: int
    ) -> FutureTransactionResponse:
        """Scrap (cancel) a future transaction before it's due."""
        future_txn = await self.future_repo.get_by_transaction_id(transaction_id)
        if not future_txn:
            raise NotFoundError(f"Future transaction {transaction_id} not found")

        if future_txn.status != FutureTransactionStatus.SCHEDULED:
            raise AlreadyProcessedError("Transaction already processed or scrapped")

        # Update status to scrapped
        future_txn.status = FutureTransactionStatus.SCRAPPED
        future_txn.scrapped_by_user_id = user_id
        future_txn.processed_date = datetime.utcnow()
        await self.session.commit()

        # Publish event
        await event_publisher.add_event(
            FutureTransactionCancelledEvent(
                future_transaction_id=future_txn.id,
                transaction_id=future_txn.transaction_id,
                account_id=future_txn.account_id,
                scrapped_by_user_id=user_id,
            )
        )

        return FutureTransactionResponse.model_validate(future_txn)

    async def list_future_transactions(
        self, account_id: Optional[int] = None
    ) -> Page[FutureTransactionResponse]:
        """List future transactions with optional filters."""
        future_txns = await self.future_repo.list_paginated(account_id=account_id)
        return future_txns.map(
            lambda future_txn: FutureTransactionResponse.model_validate(future_txns)
        )

    async def get_due_transactions(
        self, target_date: date
    ) -> List[FutureTransactionResponse]:
        """Get future transactions due on a specific date."""
        future_txns = await self.future_repo.get_due(target_date)
        return [FutureTransactionResponse.model_validate(ft) for ft in future_txns]

    async def _schedule_notifications(self, future_txn) -> None:
        """Schedule notification tasks for a future transaction."""
        if not future_txn.notification_days or not future_txn.notification_users:
            return

        notification_days = future_txn.get_notification_days_list()
        notification_users = future_txn.get_notification_users_list()

        for days_before in notification_days:
            # Calculate notification date
            notification_date = future_txn.due_date - timedelta(days=days_before)

            # Only schedule if notification date is in the future
            if notification_date > date.today():
                # Schedule Celery task for notification
                celery_app.send_task(
                    "send_future_transaction_notification",
                    kwargs={
                        "future_transaction_id": future_txn.id,
                        "user_ids": notification_users,
                        "days_before": days_before,
                        "due_date": future_txn.due_date.isoformat(),
                        "amount": float(future_txn.amount),
                        "description": future_txn.description,
                    },
                    eta=datetime.combine(notification_date, datetime.min.time()),
                )

        logger.info(
            f"Scheduled {len(notification_days)} notifications for future transaction {future_txn.transaction_id}"
        )
