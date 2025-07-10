# app/services/accounts.py
from typing import Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination import Page
from app.db.repository import AccountRepository
from app.domain.schemas import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountTransactionView,
)
from app.core.exceptions import NotFoundError
from app.core.cache import cached_account_data


class AccountService:
    def __init__(self, session: AsyncSession):
        self.repo = AccountRepository(session)

    async def create_account(self, payload: AccountCreate) -> AccountResponse:
        account = await self.repo.create(payload)
        return AccountResponse.model_validate(account)

    @cached_account_data
    async def get_account(self, account_id: int) -> AccountResponse:
        account = await self.repo.get(account_id)
        if not account:
            raise NotFoundError(f"Account {account_id} not found")
        return AccountResponse.model_validate(account)

    async def update_account(
        self, account_id: int, payload: AccountUpdate
    ) -> AccountResponse:
        account = await self.repo.get(account_id)
        if not account:
            raise NotFoundError(f"Account {account_id} not found")
        account = await self.repo.update(account, payload)
        return AccountResponse.model_validate(account)

    async def list_accounts_paginated(
        self, search: Optional[str] = None, is_active: Optional[bool] = None
    ) -> Page[AccountResponse]:
        accounts_page = await self.repo.list_paginated(
            search=search, is_active=is_active
        )
        return accounts_page.map(lambda acc: AccountResponse.model_validate(acc))

    @cached_account_data
    async def get_account_transactions(
        self,
        account_id: int,
        start_date: date,
        end_date: date,
    ) -> AccountTransactionView:
        accounts = await self.repo.list_view(account_id)
        if not accounts:
            raise NotFoundError(f"Account {account_id} not found")
        return [AccountResponse.model_validate(a) for a in accounts]
