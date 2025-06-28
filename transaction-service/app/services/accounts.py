# app/services/accounts.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repository import AccountRepository
from app.domain.schemas import AccountCreate, AccountUpdate, AccountResponse
from app.core.exceptions import NotFoundError
from app.core.cache import cached_account_data


class AccountService:
    def __init__(self, session: AsyncSession):
        self.repo = AccountRepository(session)

    async def create_account(self, payload: AccountCreate) -> AccountResponse:
        account = await self.repo.create(payload)
        return AccountResponse.model_validate(account)

    @cached_account_data(ttl=300)
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

    async def list_accounts(
        self, skip=0, limit=100, is_active: Optional[bool] = None
    ) -> List[AccountResponse]:
        accounts = await self.repo.list(skip, limit, is_active)
        return [AccountResponse.model_validate(a) for a in accounts]
