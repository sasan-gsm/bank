# app/domain/models.py

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
from .enums import (
    TransactionStatus,
    TransactionCategory,
    FutureTransactionTrigger,
    FutureTransactionStatus,
)


class Account(BaseModel):
    __tablename__ = "accounts"

    account_number = Column(String(50), unique=True, index=True, nullable=False)
    bank_name = Column(String(100), nullable=False)
    current_balance = Column(Numeric(15, 2), nullable=False, default=0.00)
    available_balance = Column(Numeric(15, 2), nullable=False, default=0.00)
    is_active = Column(Boolean, default=True, nullable=False)

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    future_transactions: Mapped[List["FutureTransaction"]] = relationship(
        "FutureTransaction", back_populates="account", cascade="all, delete-orphan"
    )


class Transaction(BaseModel):
    __tablename__ = "transactions"

    transaction_id = Column(String(50), unique=True, index=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=False)

    category = Column(DbEnum(TransactionCategory), nullable=False)
    status = Column(
        DbEnum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING
    )

    transaction_date = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    processed_date = Column(DateTime(timezone=True), nullable=True)

    created_by_user_id = Column(Integer, nullable=False)
    verified_by_user_id = Column(Integer, nullable=True)

    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    account: Mapped["Account"] = relationship("Account", back_populates="transactions")


class FutureTransaction(BaseModel):
    __tablename__ = "future_transactions"

    transaction_id = Column(String(50), unique=True, index=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(DbEnum(TransactionCategory), nullable=False)

    due_date = Column(Date, nullable=False)
    trigger_type = Column(
        DbEnum(FutureTransactionTrigger),
        nullable=False,
        default=FutureTransactionTrigger.AUTOMATIC,
    )
    status = Column(
        DbEnum(FutureTransactionStatus),
        nullable=False,
        default=FutureTransactionStatus.SCHEDULED,
    )

    triggered_date = Column(DateTime(timezone=True), nullable=True)
    processed_date = Column(DateTime(timezone=True), nullable=True)

    created_by_user_id = Column(Integer, nullable=False)
    triggered_by_user_id = Column(Integer, nullable=True)
    scrapped_by_user_id = Column(Integer, nullable=True)

    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    notification_days = Column(String(100), nullable=True)
    notification_users = Column(String(500), nullable=True)

    account: Mapped["Account"] = relationship(
        "Account", back_populates="future_transactions"
    )

    def get_notification_days_list(self) -> List[int]:
        return (
            [int(x) for x in self.notification_days.split(",") if x.strip().isdigit()]
            if self.notification_days
            else []
        )

    def get_notification_users_list(self) -> List[int]:
        return (
            [int(x) for x in self.notification_users.split(",") if x.strip().isdigit()]
            if self.notification_users
            else []
        )
