from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination import Page
from app.domain.schemas import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountTransactionView,
)
from app.services.accounts import AccountService
from app.db.session import get_db
from app.api.deps import (
    require_manage_bank_accounts,
    require_view_bank_balances,
    require_view_transactions,
)
from app.core.exceptions import NotFoundError
from datetime import datetime, timedelta

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(
    payload: AccountCreate,
    user=Depends(require_manage_bank_accounts),
    db: AsyncSession = Depends(get_db),
):
    return await AccountService(db).create_account(payload)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account_endpoint(
    account_id: int,
    user=Depends(require_view_bank_balances),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await AccountService(db).get_account(account_id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account_endpoint(
    account_id: int,
    payload: AccountUpdate,
    user=Depends(require_manage_bank_accounts),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await AccountService(db).update_account(account_id, payload)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=Page[AccountResponse])
async def list_accounts_endpoint(
    search: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    user=Depends(require_view_bank_balances),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await AccountService(db).list_accounts_paginated(
            search=search,
            is_active=is_active,
            user_id=user["user_id"],
        )
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{account_id}")
async def delete_account_endpoint(
    account_id: int,
    user=Depends(require_manage_bank_accounts),
    db: AsyncSession = Depends(get_db),
):
    try:
        await AccountService(db).delete_account(account_id, user["user_id"])
        return {"message": "Account deleted successfully"}
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{account_id}/transactions", response_model=AccountTransactionView)
async def get_account_transactions_view(
    account_id: int,
    start_date: datetime = Query(
        default_factory=lambda: datetime.now() - timedelta(days=30)
    ),
    end_date: datetime = Query(default_factory=datetime.now),
    include_future: bool = Query(True),
    user=Depends(require_view_transactions),
    db: AsyncSession = Depends(get_db),
):
    """Get account transactions in column view format"""
    try:
        return await AccountService(db).get_account_transactions(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            include_future=include_future,
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
