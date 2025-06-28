# app/services/balances.py

from decimal import Decimal
from typing import List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import AccountRepository
from app.domain.models import Account, Transaction
from app.domain.schemas import BalanceSummary
from app.core.enums import TransactionStatus, TransactionCategory
from app.core.cache import cached_account_balance
from app.core.exceptions import NotFoundError


class BalanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)

    @cached_account_balance(ttl=60)
    async def get_account_balance(self, account_id: int) -> BalanceSummary:
        account = await self.repo.get(account_id)
        if not account:
            raise NotFoundError(f"Account {account_id} not found")

        pending_count = await self._count_pending(account_id)
        last_txn_date = await self._last_transaction_date(account_id)

        return BalanceSummary(
            account_id=account.id,
            account_number=account.account_number,
            account_name=account.account_name,
            current_balance=account.current_balance,
            available_balance=account.available_balance,
            pending_transactions_count=pending_count,
            last_transaction_date=last_txn_date,
        )

    async def get_all_balances(self) -> List[BalanceSummary]:
        accounts = await self.repo.list(is_active=True)
        return [await self.get_account_balance(a.id) for a in accounts]

    async def recalculate_balance(self, account_id: int) -> BalanceSummary:
        account = await self.repo.get(account_id)
        if not account:
            raise NotFoundError(f"Account {account_id} not found")

        income_total = await self._sum_transactions(
            account_id, TransactionCategory.INCOME
        )
        expense_total = await self._sum_transactions(
            account_id, TransactionCategory.EXPENSE
        )

        new_balance = income_total - expense_total
        account.current_balance = account.available_balance = new_balance

        await self.session.commit()
        await self.session.refresh(account)
        return await self.get_account_balance(account_id)

    async def _sum_transactions(
        self, account_id: int, category: TransactionCategory
    ) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.category == category,
                    Transaction.status == TransactionStatus.PROCESSED,
                )
            )
        )
        return result.scalar() or Decimal("0")

    async def _count_pending(self, account_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.status == TransactionStatus.PENDING,
                )
            )
        )
        return result.scalar() or 0

    async def _last_transaction_date(self, account_id: int):
        result = await self.session.execute(
            select(func.max(Transaction.transaction_date)).where(
                Transaction.account_id == account_id
            )
        )
        return result.scalar()
