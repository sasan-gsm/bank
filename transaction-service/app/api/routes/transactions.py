from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
    FutureTransactionCreate,
    FutureTransactionResponse,
)
from app.core.enums import TransactionStatus
from app.services.transactions import TransactionService
from app.services.future_transactions import FutureTransactionService
from app.db.session import get_db
from app.api.deps import (
    require_create_transactions,
    require_edit_transactions,
    require_verify_transactions,
    require_void_transactions,
    require_view_transactions,
)
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/transactions", tags=["transactions"])


# ———————————— Daily Transactions ————————————


@router.post(
    "/daily", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_daily(
    payload: TransactionCreate,
    user=Depends(require_create_transactions),
    db: AsyncSession = Depends(get_db),
):
    try:
        txn = await TransactionService(db).create_transaction(payload, user["user_id"])
        return txn
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/daily/{transaction_id}", response_model=TransactionResponse)
async def get_daily(
    transaction_id: str,
    user=Depends(require_view_transactions),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TransactionService(db).get_transaction(transaction_id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/daily/{transaction_id}", response_model=TransactionResponse)
async def update_daily(
    transaction_id: str,
    payload: TransactionUpdate,
    user=Depends(require_edit_transactions),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TransactionService(db).update_transaction(
            transaction_id, payload, user["user_id"]
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/daily/{transaction_id}/verify", response_model=TransactionResponse)
async def verify_daily(
    transaction_id: str,
    user=Depends(require_verify_transactions),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TransactionService(db).verify_transaction(
            transaction_id, user["user_id"]
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/daily/{transaction_id}/void", response_model=TransactionResponse)
async def void_daily(
    transaction_id: str,
    user=Depends(require_void_transactions),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TransactionService(db).void_transaction(
            transaction_id, user["user_id"]
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/daily", response_model=List[TransactionResponse])
async def list_daily(
    account_id: Optional[int] = Query(None),
    status: Optional[TransactionStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user=Depends(require_view_transactions),
    db: AsyncSession = Depends(get_db),
):
    return await TransactionService(db).list_transactions(
        account_id, skip, limit, status
    )


# ———————————— Future Transactions ————————————


@router.post(
    "/future",
    response_model=FutureTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_future(
    payload: FutureTransactionCreate,
    user=Depends(require_create_transactions),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await FutureTransactionService(db).create_future_transaction(
            payload, user["user_id"]
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/future/{transaction_id}/trigger", response_model=FutureTransactionResponse
)
async def trigger_future(
    transaction_id: str,
    user=Depends(require_verify_transactions),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await FutureTransactionService(db).trigger_future_transaction(
            transaction_id, user["user_id"]
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/future/{transaction_id}/scrap", response_model=FutureTransactionResponse)
async def scrap_future(
    transaction_id: str,
    user=Depends(require_void_transactions),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await FutureTransactionService(db).scrap_future_transaction(
            transaction_id, user["user_id"]
        )
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
