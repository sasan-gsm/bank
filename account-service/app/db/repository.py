from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from ..domain.models import Account, AccountStatus
from ..domain.schemas import AccountCreate, AccountUpdate, BalanceUpdate
import json


class AccountRepository:
    """Repository for Account aggregate operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, account_data: AccountCreate, created_by_user_id: int
    ) -> Account:
        """Create a new account."""
        # Generate unique account number
        account_number = await self._generate_account_number()

        # Create account instance - simplified
        account = Account(
            account_number=account_number,
            bank_name=account_data.bank_name,
            branch_code=account_data.branch_code,
            current_balance=account_data.initial_balance,
            available_balance=account_data.initial_balance,
            created_by_user_id=created_by_user_id,
            authorized_users=json.dumps([]),  # Start with empty authorized users
        )

        self.session.add(account)
        await self.session.flush()  # Get the ID
        await self.session.refresh(account)

        return account

    async def get_by_id(self, account_id: int) -> Optional[Account]:
        """Get account by ID."""
        result = await self.session.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_by_account_number(self, account_number: str) -> Optional[Account]:
        """Get account by account number."""
        result = await self.session.execute(
            select(Account).where(Account.account_number == account_number)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: int, include_authorized: bool = True
    ) -> List[Account]:
        """Get all accounts for a user (owned + authorized)."""
        if include_authorized:
            # Get accounts where user is owner or authorized
            result = await self.session.execute(
                select(Account)
                .where(
                    or_(
                        Account.owner_user_id == user_id,
                        Account.authorized_users.like(f"%{user_id}%"),
                    )
                )
                .order_by(Account.created_at.desc())
            )
        else:
            # Get only owned accounts
            result = await self.session.execute(
                select(Account)
                .where(Account.owner_user_id == user_id)
                .order_by(Account.created_at.desc())
            )

        accounts = result.scalars().all()

        # Filter authorized accounts properly (JSON contains check)
        if include_authorized:
            filtered_accounts = []
            for account in accounts:
                if account.owner_user_id == user_id or account.is_user_authorized(
                    user_id
                ):
                    filtered_accounts.append(account)
            return filtered_accounts

        return list(accounts)

    async def update(
        self, account_id: int, account_data: AccountUpdate, updated_by_user_id: int
    ) -> Optional[Account]:
        """Update account information."""
        account = await self.get_by_id(account_id)
        if not account:
            return None

        # Update fields that are provided - simplified
        update_data = account_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(account, field):
                if field == "status" and isinstance(value, AccountStatus):
                    setattr(account, field, value.value)
                else:
                    setattr(account, field, value)

        account.last_modified_by_user_id = updated_by_user_id

        await self.session.flush()
        await self.session.refresh(account)

        return account

    async def update_balance(
        self, account_id: int, balance_update: BalanceUpdate, updated_by_user_id: int
    ) -> Optional[Account]:
        """Update account balance using domain logic."""
        account = await self.get_by_id(account_id)
        if not account:
            return None

        # Store previous balance for event publishing
        previous_balance = account.current_balance

        # Use domain logic for balance update
        account.update_balance(balance_update.amount, balance_update.is_credit)
        account.last_modified_by_user_id = updated_by_user_id

        await self.session.flush()
        await self.session.refresh(account)

        return account

    async def activate(
        self, account_id: int, activated_by_user_id: int
    ) -> Optional[Account]:
        """Activate account."""
        account = await self.get_by_id(account_id)
        if not account:
            return None

        account.activate()
        account.last_modified_by_user_id = activated_by_user_id

        await self.session.flush()
        await self.session.refresh(account)

        return account

    async def deactivate(
        self, account_id: int, deactivated_by_user_id: int, reason: Optional[str] = None
    ) -> Optional[Account]:
        """Deactivate account."""
        account = await self.get_by_id(account_id)
        if not account:
            return None

        account.deactivate(reason)
        account.last_modified_by_user_id = deactivated_by_user_id

        await self.session.flush()
        await self.session.refresh(account)

        return account

    async def add_authorized_user(
        self, account_id: int, user_id: int, added_by_user_id: int
    ) -> Optional[Account]:
        """Add authorized user to account."""
        account = await self.get_by_id(account_id)
        if not account:
            return None

        account.add_authorized_user(user_id)
        account.last_modified_by_user_id = added_by_user_id

        await self.session.flush()
        await self.session.refresh(account)

        return account

    async def remove_authorized_user(
        self, account_id: int, user_id: int, removed_by_user_id: int
    ) -> Optional[Account]:
        """Remove authorized user from account."""
        account = await self.get_by_id(account_id)
        if not account:
            return None

        account.remove_authorized_user(user_id)
        account.last_modified_by_user_id = removed_by_user_id

        await self.session.flush()
        await self.session.refresh(account)

        return account

    async def delete(self, account_id: int) -> bool:
        """Soft delete account (set status to closed)."""
        account = await self.get_by_id(account_id)
        if not account:
            return False

        account.status = AccountStatus.CLOSED.value
        account.is_active = False

        await self.session.flush()
        return True

    async def get_accounts_by_status(
        self, status: AccountStatus, limit: int = 100, offset: int = 0
    ) -> List[Account]:
        """Get accounts by status with pagination."""
        result = await self.session.execute(
            select(Account)
            .where(Account.status == status.value)
            .order_by(Account.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    # Removed get_accounts_by_type method as account types are no longer used

    async def search_accounts(
        self,
        query: str,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Account]:
        """Search accounts by name, number, or bank name."""
        search_filter = or_(
            Account.account_number.ilike(f"%{query}%"),
            Account.bank_name.ilike(f"%{query}%"),
        )

        if user_id:
            search_filter = and_(
                search_filter,
                or_(
                    Account.authorized_users.like(f"%{user_id}%"),
                ),
            )

        result = await self.session.execute(
            select(Account)
            .where(search_filter)
            .order_by(Account.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        accounts = list(result.scalars().all())

        # Filter authorized accounts properly if user_id is provided
        if user_id:
            filtered_accounts = []
            for account in accounts:
                if account.owner_user_id == user_id or account.is_user_authorized(
                    user_id
                ):
                    filtered_accounts.append(account)
            return filtered_accounts

        return accounts

    async def get_account_statistics(
        self, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get account statistics."""
        base_query = select(Account)

        if user_id:
            base_query = base_query.where(
                or_(
                    Account.owner_user_id == user_id,
                    Account.authorized_users.like(f"%{user_id}%"),
                )
            )

        # Total accounts
        total_result = await self.session.execute(
            select(func.count(Account.id)).select_from(base_query.subquery())
        )
        total_accounts = total_result.scalar()

        # Active accounts
        active_result = await self.session.execute(
            select(func.count(Account.id)).select_from(
                base_query.where(Account.is_active == True).subquery()
            )
        )
        active_accounts = active_result.scalar()

        # Total balance
        balance_result = await self.session.execute(
            select(func.sum(Account.current_balance)).select_from(
                base_query.where(Account.is_active == True).subquery()
            )
        )
        total_balance = balance_result.scalar() or Decimal("0.00")

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "inactive_accounts": total_accounts - active_accounts,
            "total_balance": total_balance,
        }
