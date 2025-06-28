from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas import BalanceSummary
from app.services.balances import BalanceService
from app.db.session import get_db
from app.api.deps import require_view_bank_balances
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/balance", tags=["Balance"])


@router.get("/{account_id}", response_model=BalanceSummary)
async def get_balance(
    account_id: int,
    user=Depends(require_view_bank_balances),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await BalanceService(db).get_account_balance(account_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=List[BalanceSummary])
async def list_balances(
    user=Depends(require_view_bank_balances), db: AsyncSession = Depends(get_db)
):
    return await BalanceService(db).get_all_balances()


@router.post("/{account_id}/recalculate", response_model=BalanceSummary)
async def recalculate(
    account_id: int,
    user=Depends(require_view_bank_balances),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await BalanceService(db).recalculate_balance(account_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
