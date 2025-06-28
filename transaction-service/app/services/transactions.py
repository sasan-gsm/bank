# app/services/transactions.py

from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TransactionRepository, AccountRepository
from app.domain.schemas import TransactionCreate, TransactionUpdate, TransactionResponse
from app.core.exceptions import (
    NotFoundError,
    InsufficientBalanceError,
    AlreadyProcessedError,
)
from app.domain.enums import TransactionStatus, TransactionCategory
from app.events.publisher import (
    event_publisher,
    TransactionCreatedEvent,
    TransactionVerifiedEvent,
    TransactionVoidedEvent,
)


class TransactionService:
    def __init__(self, session: AsyncSession):
        self.txn_repo = TransactionRepository(session)
        self.acct_repo = AccountRepository(session)
        self.session = session

    async def create_transaction(
        self, payload: TransactionCreate, user_id: int
    ) -> TransactionResponse:
        account = await self.acct_repo.get(payload.account_id)
        if not account:
            raise NotFoundError(f"Account {payload.account_id} not found")

        if (
            payload.category == TransactionCategory.EXPENSE
            and account.available_balance < payload.amount
        ):
            raise InsufficientBalanceError("Insufficient funds")

        txn = await self.txn_repo.create(payload, user_id)
        credit = payload.category == TransactionCategory.INCOME
        await self.acct_repo.adjust_balance(account, payload.amount, credit)

        txn.status = TransactionStatus.PROCESSED
        txn.processed_date = datetime.utcnow()
        await self.session.commit()

        await event_publisher.add_event(
            TransactionCreatedEvent(
                transaction_id=txn.transaction_id,
                account_id=txn.account_id,
                amount=float(txn.amount),
                category=txn.category.value,
                user_id=user_id,
            )
        )
        return TransactionResponse.model_validate(txn)

    async def get_transaction(self, transaction_id: str) -> TransactionResponse:
        txn = await self.txn_repo.get_by_transaction_id(transaction_id)
        if not txn:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        return TransactionResponse.model_validate(txn)

    async def update_transaction(
        self, transaction_id: str, payload: TransactionUpdate, user_id: int
    ) -> TransactionResponse:
        txn = await self.txn_repo.get_by_transaction_id(transaction_id)
        if not txn:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        if txn.status == TransactionStatus.PROCESSED:
            raise AlreadyProcessedError("Cannot modify a processed transaction")
        txn = await self.txn_repo.update(txn, payload)
        return TransactionResponse.model_validate(txn)

    async def verify_transaction(
        self, transaction_id: str, user_id: int
    ) -> TransactionResponse:
        txn = await self.txn_repo.get_by_transaction_id(transaction_id)
        if not txn:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        if txn.status != TransactionStatus.PENDING:
            raise AlreadyProcessedError("Transaction already verified or processed")
        txn = await self.txn_repo.verify_transaction(txn, user_id)
        await event_publisher.add_event(
            TransactionVerifiedEvent(
                transaction_id=txn.transaction_id,
                account_id=txn.account_id,
                verified_by_user_id=user_id,
            )
        )
        return TransactionResponse.model_validate(txn)

    async def void_transaction(
        self, transaction_id: str, user_id: int
    ) -> TransactionResponse:
        txn = await self.txn_repo.get_by_transaction_id(transaction_id)
        if not txn:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        if txn.status == TransactionStatus.PROCESSED:
            account = await self.acct_repo.get(txn.account_id)
            if account:
                credit = txn.category == TransactionCategory.EXPENSE
                await self.acct_repo.adjust_balance(account, txn.amount, credit)
        txn = await self.txn_repo.void_transaction(txn)
        await event_publisher.add_event(
            TransactionVoidedEvent(
                transaction_id=txn.transaction_id,
                account_id=txn.account_id,
                voided_by_user_id=user_id,
            )
        )
        return TransactionResponse.model_validate(txn)

    async def list_transactions(
        self, account_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[TransactionResponse]:
        if account_id:
            txns = await self.txn_repo.list_by_account(account_id, skip, limit)
        else:
            txns = await self.txn_repo.list_all(skip, limit)
        return [TransactionResponse.model_validate(txn) for txn in txns]
