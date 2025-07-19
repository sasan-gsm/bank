from sqlalchemy import Integer, String, Boolean, Numeric, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import registry, Mapped, mapped_column
from enum import Enum
from decimal import Decimal

mapped_registery = registry()
Base = mapped_registery.generate_base()


class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    account_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    # Financial data - simplified to core balance tracking
    current_balance: Mapped[int] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )
    available_balance: Mapped[int] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )

    # Account details
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    branch_code: Mapped[str] = mapped_column(String(20), nullable=True)

    # Status and metadata
    status: Mapped[AccountStatus] = mapped_column(
        SQLEnum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_modified_by_user_id: Mapped[int] = mapped_column(Integer, nullable=True)
