# app/db/repository.py
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.domain.models import Account, Transaction, FutureTransaction
from app.domain.schemas import (
    AccountCreate,
    AccountUpdate,
    TransactionCreate,
    TransactionUpdate,
    FutureTransactionCreate,
)
from app.core.cache import cache_manager
from app.core.exceptions import (
    NotFoundError,
    InsufficientBalanceError,
    InvalidTransactionError,
)
from datetime import date
import uuid


class AccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, account_id: int) -> Optional[Account]:
        result = await self.session.execute(
            select(Account).where(
                and_(Account.id == account_id, Account.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, payload: AccountCreate) -> Account:
        account = Account(**payload.model_dump())
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        await cache_manager.invalidate_account(account.id)
        return account

    async def update(self, account: Account, payload: AccountUpdate) -> Account:
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(account, k, v)
        await self.session.commit()
        await self.session.refresh(account)
        await cache_manager.invalidate_account(account.id)
        return account

    async def list(
        self, skip=0, limit=100, active: Optional[bool] = None
    ) -> List[Account]:
        q = select(Account).where(Account.is_deleted == False)
        if active is not None:
            q = q.where(Account.is_active == active)
        q = q.offset(skip).limit(limit).order_by(desc(Account.created_at))
        return (await self.session.execute(q)).scalars().all()

    async def adjust_balance(
        self, account: Account, amount: Decimal, credit: bool = True
    ) -> Account:
        if not credit and account.current_balance < amount:
            raise InsufficientBalanceError("Not enough funds")
        delta = amount if credit else -amount
        account.current_balance += delta
        account.available_balance += delta
        await self.session.commit()
        await cache_manager.invalidate_account(account.id)
        return account


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, txn_id: int) -> Transaction:
        tx = (
            await self.session.execute(
                select(Transaction)
                .options(selectinload(Transaction.account))
                .where(and_(Transaction.id == txn_id, Transaction.is_deleted == False))
            )
        ).scalar_one_or_none()
        if not tx:
            raise NotFoundError("Transaction not found")
        return tx

    async def create(self, payload: TransactionCreate, user_id: int) -> Transaction:
        if payload.amount <= 0:
            raise InvalidTransactionError("Amount must be positive")
        tx = Transaction(
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            **payload.model_dump(exclude={"id"}),
            created_by_user_id=user_id,
        )
        self.session.add(tx)
        await self.session.commit()
        await self.session.refresh(tx)
        return tx

    async def update(self, tx: Transaction, payload: TransactionUpdate):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(tx, k, v)
        await self.session.commit()
        await self.session.refresh(tx)
        return tx

    async def list_by_account(
        self, account_id: int, skip=0, limit=100
    ) -> List[Transaction]:
        q = select(Transaction).where(
            and_(Transaction.account_id == account_id, Transaction.is_deleted == False)
        )
        q = q.offset(skip).limit(limit).order_by(desc(Transaction.transaction_date))
        return (await self.session.execute(q)).scalars().all()


class FutureTransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_due(self, target_date: date) -> List[FutureTransaction]:
        q = select(FutureTransaction).filter(
            FutureTransaction.due_date == target_date,
            FutureTransaction.status == FutureTransaction.SCHEDULED,
            FutureTransaction.is_deleted == False,
        )
        return (await self.session.execute(q)).scalars().all()

    async def create(
        self, payload: FutureTransactionCreate, user_id: int
    ) -> FutureTransaction:
        ft = FutureTransaction(
            transaction_id=f"FTX-{uuid.uuid4().hex[:12].upper()}",
            **payload.model_dump(
                exclude={"id", "notification_days", "notification_users"}
            ),
            created_by_user_id=user_id,
            notification_days=",".join(map(str, payload.notification_days))
            if payload.notification_days
            else None,
            notification_users=",".join(map(str, payload.notification_users))
            if payload.notification_users
            else None,
        )
        self.session.add(ft)
        await self.session.commit()
        await self.session.refresh(ft)
        return ft
