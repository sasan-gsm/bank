from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .enums import (
    TransactionStatus,
    TransactionCategory,
    FutureTransactionTrigger,
    FutureTransactionStatus,
)

# ------------------ ACCOUNT ------------------


class AccountBase(BaseModel):
    account_number: str = Field(..., min_length=5, max_length=50)
    account_name: str = Field(..., max_length=100)
    bank_name: str = Field(..., max_length=100)

    model_config = ConfigDict(from_attributes=True)


class AccountCreate(AccountBase):
    initial_balance: Decimal = Field(default=Decimal("0.00"), ge=0)


class AccountUpdate(BaseModel):
    account_name: Optional[str] = Field(None, max_length=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class AccountResponse(AccountBase):
    id: int
    current_balance: Decimal
    available_balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountTransactionView(AccountBase):
    id: int
    account_number: str
    current_balance: Decimal
    available_balance: Decimal
    start_date: date
    end_date: date

    model_config = ConfigDict(from_attributes=True)


# ------------------ TRANSACTION ------------------


class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: str = Field(..., max_length=500)
    category: TransactionCategory
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v > Decimal("1000000.00"):
            raise ValueError("Transaction amount exceeds limit")
        return v

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(TransactionBase):
    account_id: int
    transaction_date: Optional[datetime] = None


class TransactionUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[TransactionCategory] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(TransactionBase):
    id: int
    transaction_id: str
    account_id: int
    status: TransactionStatus
    transaction_date: datetime
    processed_date: Optional[datetime]
    created_by_user_id: int
    verified_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ FUTURE TRANSACTION ------------------


class FutureTransactionBase(TransactionBase):
    due_date: date
    trigger_type: FutureTransactionTrigger = FutureTransactionTrigger.AUTOMATIC
    notification_days: Optional[List[int]] = None
    notification_users: Optional[List[int]] = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: date) -> date:
        if v <= date.today():
            raise ValueError("Due date must be in the future")
        return v


class FutureTransactionCreate(FutureTransactionBase):
    account_id: int


class FutureTransactionUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[TransactionCategory] = None
    due_date: Optional[date] = None
    trigger_type: Optional[FutureTransactionTrigger] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)
    notification_days: Optional[List[int]] = None
    notification_users: Optional[List[int]] = None

    model_config = ConfigDict(from_attributes=True)


class FutureTransactionResponse(FutureTransactionBase):
    id: int
    transaction_id: str
    account_id: int
    status: FutureTransactionStatus
    triggered_date: Optional[datetime]
    processed_date: Optional[datetime]
    created_by_user_id: int
    triggered_by_user_id: Optional[int]
    scrapped_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ MISC ------------------


class BalanceSummary(BaseModel):
    account_id: int
    account_number: str
    account_name: str
    current_balance: Decimal
    available_balance: Decimal
    pending_transactions_count: int
    last_transaction_date: Optional[datetime]


class TransactionSummary(BaseModel):
    total_transactions: int
    total_amount: Decimal
    pending_count: int
    verified_count: int
    processed_count: int
    voided_count: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ------------------ PAGINATED RESPONSE ------------------
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    next: Optional[str] = None
    previous: Optional[str] = None
    count: Optional[int] = None
