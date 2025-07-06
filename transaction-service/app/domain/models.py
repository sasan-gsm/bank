from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
    Text,
    Enum as DbEnum,
)
from sqlalchemy.orm import relationship, Mapped
from app.db.base import BaseModel


# app/domain/models.py
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, Text, Numeric, DateTime, Date, Boolean, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Account(BaseModel):
    """Account model with SQLAlchemy 2.0 mapped_column syntax."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), default=Decimal("0.00"), nullable=False
    )
    available_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="IRR", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships with proper typing
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    future_transactions: Mapped[List["FutureTransaction"]] = relationship(
        "FutureTransaction", back_populates="account", cascade="all, delete-orphan"
    )


class Transaction(BaseModel):
    """Transaction model with SQLAlchemy 2.0 mapped_column syntax."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # TransactionCategory enum
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # TransactionStatus enum
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    processed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reference_number: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_user_id: Mapped[int] = mapped_column(nullable=False)
    verified_by_user_id: Mapped[Optional[int]]

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")


class FutureTransaction(BaseModel):
    """Future transaction model with SQLAlchemy 2.0 mapped_column syntax."""

    __tablename__ = "future_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    triggered_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reference_number: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    notification_days: Mapped[Optional[str]] = mapped_column(String(255))
    notification_users: Mapped[Optional[str]] = mapped_column(String(255))
    created_by_user_id: Mapped[int] = mapped_column(nullable=False)
    triggered_by_user_id: Mapped[Optional[int]]
    scrapped_by_user_id: Mapped[Optional[int]]

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account", back_populates="future_transactions"
    )
