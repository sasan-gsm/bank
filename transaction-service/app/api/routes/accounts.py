from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas import AccountCreate, AccountUpdate, AccountResponse
from app.services.accounts import AccountService
from app.db.session import get_db
from app.api.deps import require_manage_bank_accounts, require_view_bank_balances
from app.core.exceptions import NotFoundError

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


@router.get("/", response_model=List[AccountResponse])
async def list_accounts_endpoint(
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user=Depends(require_view_bank_balances),
    db: AsyncSession = Depends(get_db),
):
    return await AccountService(db).list_accounts(
        skip=skip, limit=limit, is_active=is_active
    )
