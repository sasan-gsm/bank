from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.responses import JSONResponse
from ...domain.schemas import AccountCreate, AccountUpdate, BalanceUpdate
from ...domain.models import AccountStatus
from ...services.account_service import AccountService
from ..deps import (
    get_current_active_user_id,
    get_account_service,
    validate_pagination,
    validate_search_query,
    create_success_response,
    create_error_response,
    log_request_info,
    rate_limit_check,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"],
    dependencies=[Depends(log_request_info), Depends(rate_limit_check)],
)


# Account CRUD Operations


@router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
    description="Create a new bank account for the authenticated user",
)
async def create_account(
    account_data: AccountCreate,
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Create a new account."""
    try:
        account = await account_service.create_account(account_data, user_id, user_id)

        return create_success_response(
            account.model_dump(), "Account created successfully"
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account",
        )


@router.get(
    "/{account_id}",
    response_model=dict,
    summary="Get account by ID",
    description="Retrieve account details by account ID",
)
async def get_account(
    account_id: int = Path(..., description="Account ID"),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Get account by ID."""
    account = await account_service.get_account(account_id, user_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied",
        )

    return create_success_response(
        account.model_dump(), "Account retrieved successfully"
    )


@router.get(
    "/number/{account_number}",
    response_model=dict,
    summary="Get account by account number",
    description="Retrieve account details by account number",
)
async def get_account_by_number(
    account_number: str = Path(..., description="Account number"),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Get account by account number."""
    account = await account_service.get_account_by_number(account_number, user_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied",
        )

    return create_success_response(
        account.model_dump(), "Account retrieved successfully"
    )


@router.put(
    "/{account_id}",
    response_model=dict,
    summary="Update account",
    description="Update account information",
)
async def update_account(
    account_data: AccountUpdate,
    account_id: int = Path(..., description="Account ID"),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Update account information."""
    try:
        account = await account_service.update_account(
            account_id, account_data, user_id
        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found or access denied",
            )

        return create_success_response(
            account.model_dump(), "Account updated successfully"
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update account {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update account",
        )


# User Accounts


@router.get(
    "/user/me",
    response_model=dict,
    summary="Get my accounts",
    description="Get all accounts for the authenticated user",
)
async def get_my_accounts(
    include_authorized: bool = Query(
        True, description="Include accounts where user is authorized"
    ),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Get all accounts for the authenticated user."""
    accounts = await account_service.get_user_accounts(
        user_id, user_id, include_authorized
    )

    return create_success_response(
        [account.model_dump() for account in accounts],
        f"Retrieved {len(accounts)} accounts",
    )


@router.get(
    "/user/{user_id}",
    response_model=dict,
    summary="Get user accounts (Admin only)",
    description="Get all accounts for a specific user (admin access required)",
)
async def get_user_accounts(
    target_user_id: int = Path(..., alias="user_id", description="Target user ID"),
    include_authorized: bool = Query(
        True, description="Include accounts where user is authorized"
    ),
    requesting_user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Get all accounts for a specific user (admin only)."""
    accounts = await account_service.get_user_accounts(
        target_user_id, requesting_user_id, include_authorized
    )

    return create_success_response(
        [account.model_dump() for account in accounts],
        f"Retrieved {len(accounts)} accounts for user {target_user_id}",
    )


# Balance Operations


@router.patch(
    "/{account_id}/balance",
    response_model=dict,
    summary="Update account balance",
    description="Update account balance with credit or debit transaction",
)
async def update_balance(
    balance_update: BalanceUpdate,
    account_id: int = Path(..., description="Account ID"),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Update account balance."""
    try:
        account = await account_service.update_balance(
            account_id, balance_update, user_id
        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found or access denied",
            )

        return create_success_response(
            account.model_dump(),
            f"Balance updated: {balance_update.amount} ({'credit' if balance_update.is_credit else 'debit'})",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update balance for account {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update balance",
        )


# Account Status Operations


@router.patch(
    "/{account_id}/activate",
    response_model=dict,
    summary="Activate account",
    description="Activate an inactive account",
)
async def activate_account(
    account_id: int = Path(..., description="Account ID"),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Activate account."""
    try:
        account = await account_service.activate_account(account_id, user_id)

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found or access denied",
            )

        return create_success_response(
            account.model_dump(), "Account activated successfully"
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to activate account {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate account",
        )


@router.patch(
    "/{account_id}/deactivate",
    response_model=dict,
    summary="Deactivate account",
    description="Deactivate an active account",
)
async def deactivate_account(
    account_id: int = Path(..., description="Account ID"),
    reason: Optional[str] = Body(None, description="Reason for deactivation"),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Deactivate account."""
    try:
        account = await account_service.deactivate_account(account_id, user_id, reason)

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found or access denied",
            )

        return create_success_response(
            account.model_dump(), "Account deactivated successfully"
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to deactivate account {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate account",
        )


# Authorization Management


@router.post(
    "/{account_id}/authorized-users/{user_id}",
    response_model=dict,
    summary="Add authorized user",
    description="Add a user to the account's authorized users list",
)
async def add_authorized_user(
    account_id: int = Path(..., description="Account ID"),
    target_user_id: int = Path(
        ..., alias="user_id", description="User ID to authorize"
    ),
    requesting_user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Add authorized user to account."""
    try:
        account = await account_service.add_authorized_user(
            account_id, target_user_id, requesting_user_id
        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found or access denied",
            )

        return create_success_response(
            account.model_dump(), f"User {target_user_id} added as authorized user"
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add authorized user to account {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add authorized user",
        )


@router.delete(
    "/{account_id}/authorized-users/{user_id}",
    response_model=dict,
    summary="Remove authorized user",
    description="Remove a user from the account's authorized users list",
)
async def remove_authorized_user(
    account_id: int = Path(..., description="Account ID"),
    target_user_id: int = Path(..., alias="user_id", description="User ID to remove"),
    requesting_user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Remove authorized user from account."""
    try:
        account = await account_service.remove_authorized_user(
            account_id, target_user_id, requesting_user_id
        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found or access denied",
            )

        return create_success_response(
            account.model_dump(), f"User {target_user_id} removed from authorized users"
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to remove authorized user from account {account_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove authorized user",
        )


# Search and Filtering


@router.get(
    "/search",
    response_model=dict,
    summary="Search accounts",
    description="Search accounts by name, number, or bank name",
)
async def search_accounts(
    q: str = Query(..., description="Search query"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
    validated_query: str = Depends(validate_search_query),
    pagination: tuple = Depends(validate_pagination),
):
    """Search accounts."""
    limit, offset = pagination

    accounts = await account_service.search_accounts(
        validated_query, user_id, limit, offset
    )

    return create_success_response(
        [account.model_dump() for account in accounts],
        f"Found {len(accounts)} accounts matching '{validated_query}'",
    )


# Removed filter_accounts_by_type endpoint as account types are no longer supported


@router.get(
    "/filter/status/{account_status}",
    response_model=dict,
    summary="Filter accounts by status",
    description="Get accounts filtered by account status",
)
async def filter_accounts_by_status(
    account_status: AccountStatus = Path(..., description="Account status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
    pagination: tuple = Depends(validate_pagination),
):
    """Filter accounts by status."""
    limit, offset = pagination

    # Get user accounts and filter by status
    all_accounts = await account_service.get_user_accounts(user_id, user_id, True)
    filtered_accounts = [
        account for account in all_accounts if account.status == account_status.value
    ]

    # Apply pagination
    paginated_accounts = filtered_accounts[offset : offset + limit]

    return create_success_response(
        [account.model_dump() for account in paginated_accounts],
        f"Found {len(paginated_accounts)} {account_status.value} accounts",
    )


# Statistics and Summary


@router.get(
    "/summary",
    response_model=dict,
    summary="Get account summary",
    description="Get account summary for the authenticated user",
)
async def get_account_summary(
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Get account summary for user."""
    summary = await account_service.get_account_summary(user_id)

    return create_success_response(
        summary.model_dump(), "Account summary retrieved successfully"
    )


@router.get(
    "/statistics",
    response_model=dict,
    summary="Get account statistics",
    description="Get detailed account statistics",
)
async def get_account_statistics(
    user_id: int = Depends(get_current_active_user_id),
    account_service: AccountService = Depends(get_account_service),
):
    """Get account statistics."""
    stats = await account_service.get_account_statistics(user_id)

    return create_success_response(stats, "Account statistics retrieved successfully")


# Health Check


@router.get(
    "/health",
    response_model=dict,
    summary="Health check",
    description="Check the health of the accounts service",
    tags=["health"],
)
async def health_check(account_service: AccountService = Depends(get_account_service)):
    """Health check endpoint."""
    try:
        # Simple database check
        await account_service.session.execute("SELECT 1")

        return create_success_response(
            {
                "status": "healthy",
                "service": "account-service",
                "database": "connected",
            },
            "Service is healthy",
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=create_error_response("Service unhealthy", "HEALTH_CHECK_FAILED"),
        )


# Error Handlers


# @router.exception_handler(ServiceError)
# async def service_error_handler(request, exc: ServiceError):
#     """Handle service errors."""
#     return JSONResponse(
#         status_code=exc.status_code, content=create_error_response(exc.message)
#     )


# @router.exception_handler(ValueError)
# async def value_error_handler(request, exc: ValueError):
#     """Handle value errors."""
#     return JSONResponse(
#         status_code=status.HTTP_400_BAD_REQUEST, content=create_error_response(str(exc))
#     )
