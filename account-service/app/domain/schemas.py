from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .models import AccountStatus


class AccountBase(BaseModel):
    """Base account schema - simplified."""

    account_number: str = Field(..., min_length=1, max_length=100)
    bank_name: str = Field(..., min_length=1, max_length=100)

    model_config = ConfigDict(from_attributes=True)


class AccountCreate(AccountBase):
    """Schema for creating new account."""

    initial_balance: Decimal = Field(default=Decimal("0.00"), ge=0)
    branch_code: Optional[str] = Field(None, max_length=20)

    @field_validator("initial_balance")
    @classmethod
    def validate_initial_balance(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Initial balance cannot be negative")
        if v > Decimal("1000000.00"):
            raise ValueError("Initial balance exceeds maximum limit")
        return v


class AccountUpdate(BaseModel):
    """Schema for updating account - simplified."""

    bank_name: Optional[str] = Field(None, min_length=1, max_length=100)
    branch_code: Optional[str] = Field(None, max_length=20)
    status: Optional[AccountStatus] = None

    model_config = ConfigDict(from_attributes=True)


class AccountResponse(AccountBase):
    """Schema for account response - simplified."""

    id: int
    account_number: str
    current_balance: Decimal
    available_balance: Decimal
    status: AccountStatus
    is_active: bool
    branch_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BalanceUpdate(BaseModel):
    """Schema for balance updates."""

    amount: Decimal = Field(..., gt=0)
    is_credit: bool = Field(default=True)
    description: str = Field(..., min_length=1, max_length=500)
    reference_id: Optional[str] = Field(None, max_length=100)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v > Decimal("1000000.00"):
            raise ValueError("Amount exceeds transaction limit")
        return v


class AccountSummary(BaseModel):
    """Schema for account summary - simplified."""

    id: int
    account_number: str
    current_balance: Decimal
    available_balance: Decimal
    status: AccountStatus
    is_active: bool
