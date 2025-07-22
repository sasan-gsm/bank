from typing import List, Optional, Dict, Any
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.repository import AccountRepository
from ..domain.models import Account
from ..domain.schemas import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    BalanceUpdate,
    AccountSummary,
)
from ..domain.events import (
    EventPublisher,
    AccountCreatedEvent,
    AccountUpdatedEvent,
    BalanceUpdatedEvent,
    AccountStatusChangedEvent,
    UserAuthorizationEvent,
)
from ..core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class AccountService:
    """Service layer for account operations with business logic and event publishing."""

    def __init__(
        self, session: AsyncSession, event_publisher: Optional[EventPublisher] = None
    ):
        self.session = session
        self.repository = AccountRepository(session)
        self.event_publisher = event_publisher or EventPublisher()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.event_publisher.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.event_publisher.disconnect()

    # Account CRUD Operations

    async def create_account(
        self, account_data: AccountCreate, created_by_user_id: int
    ) -> AccountResponse:
        """Create a new account with business validation and event publishing."""
        try:
            # Business validation
            await self._validate_account_creation(account_data)

            # Create account
            account = await self.repository.create(account_data, created_by_user_id)

            # Commit transaction
            await self.session.commit()

            # Publish domain event
            await self._publish_account_created_event(account)

            logger.info(f"Account created: {account.account_number}")

            return AccountResponse.model_validate(account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create account: {str(e)}")
            raise

    async def get_account(
        self, account_id: int, requesting_user_id: int
    ) -> Optional[AccountResponse]:
        """Get account with permission validation."""
        account = await self.repository.get_by_id(account_id)
        if not account:
            return None

        # Check permissions
        if not self._has_account_access(account, requesting_user_id):
            logger.warning(
                f"User {requesting_user_id} denied access to account {account_id}"
            )
            return None

        return AccountResponse.model_validate(account)

    async def get_account_by_number(
        self, account_number: str, requesting_user_id: int
    ) -> Optional[AccountResponse]:
        """Get account by number with permission validation."""
        account = await self.repository.get_by_account_number(account_number)
        if not account:
            return None

        # Check permissions
        if not self._has_account_access(account, requesting_user_id):
            logger.warning(
                f"User {requesting_user_id} denied access to account {account_number}"
            )
            return None

        return AccountResponse.model_validate(account)

    async def get_user_accounts(
        self, user_id: int, requesting_user_id: int, include_authorized: bool = True
    ) -> List[AccountResponse]:
        """Get all accounts for a user with permission validation."""
        # Users can only see their own accounts unless they're admin
        if user_id != requesting_user_id and not self._is_admin_user(
            requesting_user_id
        ):
            logger.warning(
                f"User {requesting_user_id} denied access to user {user_id} accounts"
            )
            return []

        accounts = await self.repository.get_by_user_id(user_id, include_authorized)
        return [AccountResponse.model_validate(account) for account in accounts]

    async def update_account(
        self, account_id: int, account_data: AccountUpdate, requesting_user_id: int
    ) -> Optional[AccountResponse]:
        """Update account with permission validation and event publishing."""
        try:
            # Get existing account
            account = await self.repository.get_by_id(account_id)
            if not account:
                return None

            # Check permissions (only owner or admin can update)
            if not self._has_account_write_access(account, requesting_user_id):
                logger.warning(
                    f"User {requesting_user_id} denied write access to account {account_id}"
                )
                return None

            # Business validation
            await self._validate_account_update(account, account_data)

            # Store previous state for event
            previous_state = AccountResponse.model_validate(account)

            # Update account
            updated_account = await self.repository.update(
                account_id, account_data, requesting_user_id
            )

            # Commit transaction
            await self.session.commit()

            # Publish domain event
            await self._publish_account_updated_event(updated_account, previous_state)

            logger.info(
                f"Account updated: {account.account_number} by user {requesting_user_id}"
            )

            return AccountResponse.model_validate(updated_account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update account {account_id}: {str(e)}")
            raise

    # Balance Operations

    async def update_balance(
        self, account_id: int, balance_update: BalanceUpdate, requesting_user_id: int
    ) -> Optional[AccountResponse]:
        """Update account balance with validation and event publishing."""
        try:
            # Get existing account
            account = await self.repository.get_by_id(account_id)
            if not account:
                return None

            # Check permissions
            if not self._has_account_write_access(account, requesting_user_id):
                logger.warning(
                    f"User {requesting_user_id} denied balance update access to account {account_id}"
                )
                return None

            # Business validation
            await self._validate_balance_update(account, balance_update)

            # Store previous balance for event
            previous_balance = account.current_balance

            # Update balance
            updated_account = await self.repository.update_balance(
                account_id, balance_update, requesting_user_id
            )

            # Commit transaction
            await self.session.commit()

            # Publish domain event
            await self._publish_balance_updated_event(
                updated_account, previous_balance, balance_update
            )

            logger.info(
                f"Balance updated for account {account.account_number}: "
                f"{balance_update.amount} ({'credit' if balance_update.is_credit else 'debit'})"
            )

            return AccountResponse.model_validate(updated_account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update balance for account {account_id}: {str(e)}")
            raise

    # Account Status Operations

    async def activate_account(
        self, account_id: int, requesting_user_id: int
    ) -> Optional[AccountResponse]:
        """Activate account with permission validation and event publishing."""
        try:
            account = await self.repository.get_by_id(account_id)
            if not account:
                return None

            # Check permissions (only owner or admin)
            if not self._has_account_write_access(account, requesting_user_id):
                logger.warning(
                    f"User {requesting_user_id} denied activation access to account {account_id}"
                )
                return None

            # Business validation
            if account.is_active:
                raise ValueError("Account is already active")

            # Activate account
            updated_account = await self.repository.activate(
                account_id, requesting_user_id
            )

            # Commit transaction
            await self.session.commit()

            # Publish domain event
            await self._publish_status_changed_event(updated_account, "activated")

            logger.info(
                f"Account activated: {account.account_number} by user {requesting_user_id}"
            )

            return AccountResponse.model_validate(updated_account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to activate account {account_id}: {str(e)}")
            raise

    async def deactivate_account(
        self, account_id: int, requesting_user_id: int, reason: Optional[str] = None
    ) -> Optional[AccountResponse]:
        """Deactivate account with permission validation and event publishing."""
        try:
            account = await self.repository.get_by_id(account_id)
            if not account:
                return None

            # Check permissions (only owner or admin)
            if not self._has_account_write_access(account, requesting_user_id):
                logger.warning(
                    f"User {requesting_user_id} denied deactivation access to account {account_id}"
                )
                return None

            # Business validation
            if not account.is_active:
                raise ValueError("Account is already inactive")

            # Deactivate account
            updated_account = await self.repository.deactivate(
                account_id, requesting_user_id, reason
            )

            # Commit transaction
            await self.session.commit()

            # Publish domain event
            await self._publish_status_changed_event(
                updated_account, "deactivated", reason
            )

            logger.info(
                f"Account deactivated: {account.account_number} by user {requesting_user_id}"
            )

            return AccountResponse.model_validate(updated_account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to deactivate account {account_id}: {str(e)}")
            raise

    # Authorization Management

    async def add_authorized_user(
        self, account_id: int, user_id: int, requesting_user_id: int
    ) -> Optional[AccountResponse]:
        """Add authorized user with permission validation and event publishing."""
        try:
            account = await self.repository.get_by_id(account_id)
            if not account:
                return None

            # Check permissions (only owner or admin)
            if not self._has_account_write_access(account, requesting_user_id):
                logger.warning(
                    f"User {requesting_user_id} denied authorization management access to account {account_id}"
                )
                return None

            # Business validation
            if account.is_user_authorized(user_id):
                raise ValueError(f"User {user_id} is already authorized")

            # Add authorized user
            updated_account = await self.repository.add_authorized_user(
                account_id, user_id, requesting_user_id
            )

            # Commit transaction
            await self.session.commit()

            # Publish domain event
            await self._publish_user_authorization_event(
                updated_account, user_id, "added", requesting_user_id
            )

            logger.info(
                f"User {user_id} added as authorized to account {account.account_number}"
            )

            return AccountResponse.model_validate(updated_account)

        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to add authorized user to account {account_id}: {str(e)}"
            )
            raise

    async def remove_authorized_user(
        self, account_id: int, user_id: int, requesting_user_id: int
    ) -> Optional[AccountResponse]:
        """Remove authorized user with permission validation and event publishing."""
        try:
            account = await self.repository.get_by_id(account_id)
            if not account:
                return None

            # Check permissions (only owner or admin)
            if not self._has_account_write_access(account, requesting_user_id):
                logger.warning(
                    f"User {requesting_user_id} denied authorization management access to account {account_id}"
                )
                return None

            # Business validation
            if not account.is_user_authorized(user_id):
                raise ValueError(f"User {user_id} is not authorized")

            # Remove authorized user
            updated_account = await self.repository.remove_authorized_user(
                account_id, user_id, requesting_user_id
            )

            # Commit transaction
            await self.session.commit()

            # Publish domain event
            await self._publish_user_authorization_event(
                updated_account, user_id, "removed", requesting_user_id
            )

            logger.info(
                f"User {user_id} removed from authorized users of account {account.account_number}"
            )

            return AccountResponse.model_validate(updated_account)

        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to remove authorized user from account {account_id}: {str(e)}"
            )
            raise

    # Search and Statistics

    async def search_accounts(
        self, query: str, requesting_user_id: int, limit: int = 100, offset: int = 0
    ) -> List[AccountResponse]:
        """Search accounts with permission filtering."""
        # Regular users can only search their own accounts
        user_filter = (
            None if self._is_admin_user(requesting_user_id) else requesting_user_id
        )

        accounts = await self.repository.search_accounts(
            query, user_filter, limit, offset
        )

        return [AccountResponse.model_validate(account) for account in accounts]

    async def get_account_statistics(self, requesting_user_id: int) -> Dict[str, Any]:
        """Get account statistics with permission filtering."""
        # Regular users get stats for their accounts only
        user_filter = (
            None if self._is_admin_user(requesting_user_id) else requesting_user_id
        )

        return await self.repository.get_account_statistics(user_filter)

    async def get_account_summary(self, requesting_user_id: int) -> AccountSummary:
        """Get account summary for user."""
        accounts = await self.repository.get_by_user_id(requesting_user_id, True)

        total_balance = sum(acc.current_balance for acc in accounts if acc.is_active)
        active_count = sum(1 for acc in accounts if acc.is_active)

        return AccountSummary(
            total_accounts=len(accounts),
            active_accounts=active_count,
            total_balance=total_balance,
        )

    # Permission Helpers

    def _has_account_access(self, account: Account, user_id: int) -> bool:
        """Check if user has read access to account."""
        return (
            account.owner_user_id == user_id
            or account.is_user_authorized(user_id)
            or self._is_admin_user(user_id)
        )

    def _has_account_write_access(self, account: Account, user_id: int) -> bool:
        """Check if user has write access to account."""
        return account.owner_user_id == user_id or self._is_admin_user(user_id)

    def _is_admin_user(self, user_id: int) -> bool:
        """Check if user is admin (placeholder - implement based on your auth system)."""
        # TODO: Implement admin check based on your authentication system
        # This could check user roles from JWT token or external service
        return False

    # Validation Helpers

    async def _validate_account_creation(self, account_data: AccountCreate):
        """Validate account creation business rules - simplified."""
        # Validate initial balance
        if account_data.initial_balance < 0:
            raise ValueError("Initial balance cannot be negative")

    async def _validate_account_update(
        self, account: Account, account_data: AccountUpdate
    ):
        """Validate account update business rules."""
        # Add any business validation rules for account updates
        if account_data.status and account_data.status.value == "closed":
            if account.current_balance != 0:
                raise ValueError("Cannot close account with non-zero balance")

    async def _validate_balance_update(
        self, account: Account, balance_update: BalanceUpdate
    ):
        """Validate balance update business rules."""
        if not account.is_active:
            raise ValueError("Cannot update balance for inactive account")

        # Check sufficient funds for debit operations
        if not balance_update.is_credit:
            if account.available_balance < balance_update.amount:
                raise ValueError("Insufficient funds for this transaction")

    # Event Publishing Helpers

    async def _publish_account_created_event(self, account: Account):
        """Publish account created event."""
        try:
            event = AccountCreatedEvent(
                account_id=account.id,
                account_number=account.account_number,
                bank_name=account.bank_name,
                initial_balance=account.current_balance,
            )
            await self.event_publisher.publish_account_created(event)
        except Exception as e:
            logger.error(f"Failed to publish account created event: {str(e)}")

    async def _publish_account_updated_event(
        self, account: Account, previous_state: AccountResponse
    ):
        """Publish account updated event."""
        try:
            event = AccountUpdatedEvent(
                account_id=account.id,
                account_number=account.account_number,
                updated_fields=self._get_updated_fields(account, previous_state),
                updated_by_user_id=account.last_modified_by_user_id,
            )
            await self.event_publisher.publish_account_updated(event)
        except Exception as e:
            logger.error(f"Failed to publish account updated event: {str(e)}")

    async def _publish_balance_updated_event(
        self, account: Account, previous_balance: Decimal, balance_update: BalanceUpdate
    ):
        """Publish balance updated event."""
        try:
            event = BalanceUpdatedEvent(
                account_id=account.id,
                account_number=account.account_number,
                previous_balance=previous_balance,
                new_balance=account.current_balance,
                amount=balance_update.amount,
                is_credit=balance_update.is_credit,
                updated_by_user_id=account.last_modified_by_user_id,
            )
            await self.event_publisher.publish_balance_updated(event)
        except Exception as e:
            logger.error(f"Failed to publish balance updated event: {str(e)}")

    async def _publish_status_changed_event(
        self, account: Account, action: str, reason: Optional[str] = None
    ):
        """Publish account status changed event."""
        try:
            event = AccountStatusChangedEvent(
                account_id=account.id,
                account_number=account.account_number,
                new_status=account.status,
                action=action,
                reason=reason,
                changed_by_user_id=account.last_modified_by_user_id,
            )
            await self.event_publisher.publish_status_changed(event)
        except Exception as e:
            logger.error(f"Failed to publish status changed event: {str(e)}")

    async def _publish_user_authorization_event(
        self, account: Account, user_id: int, action: str, changed_by_user_id: int
    ):
        """Publish user authorization event."""
        try:
            event = UserAuthorizationEvent(
                account_id=account.id,
                account_number=account.account_number,
                user_id=user_id,
                action=action,
                changed_by_user_id=changed_by_user_id,
            )
            await self.event_publisher.publish_user_authorization(event)
        except Exception as e:
            logger.error(f"Failed to publish user authorization event: {str(e)}")

    def _get_updated_fields(
        self, account: Account, previous_state: AccountResponse
    ) -> Dict[str, Any]:
        """Get fields that were updated."""
        updated_fields = {}
        current_state = AccountResponse.model_validate(account)

        for field in current_state.model_fields:
            current_value = getattr(current_state, field)
            previous_value = getattr(previous_state, field)
            if current_value != previous_value:
                updated_fields[field] = {"old": previous_value, "new": current_value}

        return updated_fields
