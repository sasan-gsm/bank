from typing import Generator, Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.security import (
    get_current_user,
    get_current_active_user,
    require_permissions,
    get_admin_user,
)
from ..core.config import get_settings
from ..db.session import get_db
from ..services.account_service import AccountService
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Security dependencies
security = HTTPBearer()


# Database Dependencies


async def get_database_session() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_db():
        yield session


# Service Dependencies


async def get_account_service(
    session: AsyncSession = Depends(get_database_session),
) -> AccountService:
    """Get account service with database session."""
    async with AccountService(session) as service:
        yield service


# Authentication Dependencies


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Extract current user ID from JWT token."""
    user_data = await get_current_user(credentials)
    return user_data.user_id


async def get_current_active_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Extract current active user ID from JWT token."""
    user_data = await get_current_active_user(await get_current_user(credentials))
    return user_data.user_id


async def get_admin_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Extract admin user ID from JWT token."""
    user_data = await get_admin_user(
        await get_current_active_user(await get_current_user(credentials))
    )
    return user_data.user_id


# Permission Dependencies


def require_account_permissions(permissions: List[str]):
    """Require specific account permissions."""
    permission_dependency = require_permissions(permissions)

    async def permission_checker(
        user_data=Depends(permission_dependency),
    ) -> int:
        return user_data.user_id

    return permission_checker


# Account-specific permission dependencies

require_account_read = require_account_permissions(["account:read"])
require_account_write = require_account_permissions(["account:write"])
require_account_admin = require_account_permissions(["account:admin"])
require_balance_update = require_account_permissions(["account:balance"])


# Validation Dependencies


async def validate_account_access(
    account_id: int,
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
) -> int:
    """Validate user has access to specific account."""
    account = await account_service.get_account(account_id, user_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied",
        )
    return account_id


async def validate_account_write_access(
    account_id: int,
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
) -> int:
    """Validate user has write access to specific account."""
    # Get account to check ownership
    account = await account_service.repository.get_by_id(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    # Check if user is owner or admin
    if not account_service._has_account_write_access(account, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to modify this account",
        )

    return account_id


# Rate Limiting Dependencies


async def rate_limit_check(request: Request) -> None:
    """Basic rate limiting check (placeholder)."""
    # TODO: Implement rate limiting logic
    # This could use Redis to track request counts per user/IP
    pass


# Request Validation Dependencies


async def validate_pagination(limit: int = 100, offset: int = 0) -> tuple[int, int]:
    """Validate pagination parameters."""
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 1000",
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be non-negative",
        )

    return limit, offset


async def validate_search_query(q: str) -> str:
    """Validate search query parameters."""
    if len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters long",
        )

    if len(q) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be less than 100 characters",
        )

    return q.strip()


# Health Check Dependencies


async def check_database_health(
    session: AsyncSession = Depends(get_database_session),
) -> bool:
    """Check database connectivity."""
    try:
        # Simple query to check database connection
        await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False


async def check_redis_health() -> bool:
    """Check Redis connectivity for events."""
    try:
        from domain.events import EventPublisher

        publisher = EventPublisher()
        await publisher.connect()
        await publisher.disconnect()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return False


# Logging Dependencies


async def log_request_info(request: Request) -> None:
    """Log request information for audit purposes."""
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )


# Error Handling Dependencies


class ServiceError(Exception):
    """Base service error."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AccountNotFoundError(ServiceError):
    """Account not found error."""

    def __init__(self, account_id: int):
        super().__init__(
            f"Account with ID {account_id} not found", status.HTTP_404_NOT_FOUND
        )


class InsufficientPermissionsError(ServiceError):
    """Insufficient permissions error."""

    def __init__(self, action: str):
        super().__init__(
            f"Insufficient permissions to {action}", status.HTTP_403_FORBIDDEN
        )


class BusinessRuleViolationError(ServiceError):
    """Business rule violation error."""

    def __init__(self, rule: str):
        super().__init__(
            f"Business rule violation: {rule}", status.HTTP_422_UNPROCESSABLE_ENTITY
        )


# Common response dependencies


def create_success_response(data: any, message: str = "Success") -> dict:
    """Create standardized success response."""
    return {"success": True, "message": message, "data": data}


def create_error_response(message: str, error_code: str = None) -> dict:
    """Create standardized error response."""
    response = {"success": False, "message": message}

    if error_code:
        response["error_code"] = error_code

    return response


# Cache Dependencies (if using fastapi-cache2)


async def get_cache_key_prefix(user_id: int = Depends(get_current_user_id)) -> str:
    """Generate cache key prefix for user-specific caching."""
    return f"user:{user_id}"


# Monitoring Dependencies


async def track_api_metrics(request: Request) -> None:
    """Track API metrics for monitoring."""
    # TODO: Implement metrics tracking
    # This could send metrics to monitoring systems like Prometheus
    pass
