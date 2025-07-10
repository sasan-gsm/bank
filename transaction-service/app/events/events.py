# app/events/events.py
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.domain.enums import TransactionType, TransactionStatus, TransactionCategory


class DomainEvent(BaseModel):
    """Base class for all domain events"""

    event_id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TransactionCreatedEvent(DomainEvent):
    """Event fired when a new transaction is created"""

    event_type: str = "transaction.created"
    transaction_id: str
    account_id: str
    amount: float
    transaction_type: TransactionType
    category: TransactionCategory
    description: str
    created_by_user_id: str
    reference_number: Optional[str] = None


class TransactionUpdatedEvent(DomainEvent):
    """Event fired when a transaction is updated"""

    event_type: str = "transaction.updated"
    transaction_id: str
    account_id: str
    old_status: TransactionStatus
    new_status: TransactionStatus
    updated_by_user_id: str
    changes: Dict[str, Any] = Field(default_factory=dict)


class TransactionDeletedEvent(DomainEvent):
    """Event fired when a transaction is deleted"""

    event_type: str = "transaction.deleted"
    transaction_id: str
    account_id: str
    amount: float
    deleted_by_user_id: str
    reason: Optional[str] = None


class FutureTransactionTriggeredEvent(DomainEvent):
    """Event fired when a future transaction is triggered"""

    event_type: str = "future_transaction.triggered"
    future_transaction_id: str
    transaction_id: str
    account_id: str
    amount: float
    triggered_date: datetime = Field(default_factory=datetime.utcnow)
    trigger_reason: str = "automatic"


class FutureTransactionCreatedEvent(DomainEvent):
    """Event fired when a future transaction is created"""

    event_type: str = "future_transaction.created"
    future_transaction_id: str
    account_id: str
    amount: float
    due_date: datetime
    created_by_user_id: str
    description: str


class FutureTransactionCancelledEvent(DomainEvent):
    """Event fired when a future transaction is cancelled"""

    event_type: str = "future_transaction.cancelled"
    future_transaction_id: str
    account_id: str
    cancelled_by_user_id: str
    cancellation_reason: Optional[str] = None


class AccountBalanceUpdatedEvent(DomainEvent):
    """Event fired when account balance is updated"""

    event_type: str = "account.balance_updated"
    account_id: str
    old_balance: float
    new_balance: float
    transaction_id: Optional[str] = None
    updated_by_user_id: str


class AccountCreatedEvent(DomainEvent):
    """Event fired when a new account is created"""

    event_type: str = "account.created"
    account_id: str
    account_number: str
    account_type: str
    initial_balance: float
    created_by_user_id: str
    owner_user_id: str


class AccountClosedEvent(DomainEvent):
    """Event fired when an account is closed"""

    event_type: str = "account.closed"
    account_id: str
    account_number: str
    final_balance: float
    closed_by_user_id: str
    closure_reason: Optional[str] = None


class LowBalanceAlertEvent(DomainEvent):
    """Event fired when account balance falls below threshold"""

    event_type: str = "account.low_balance_alert"
    account_id: str
    current_balance: float
    threshold: float
    owner_user_id: str


class HighValueTransactionEvent(DomainEvent):
    """Event fired for high-value transactions requiring special attention"""

    event_type: str = "transaction.high_value"
    transaction_id: str
    account_id: str
    amount: float
    threshold: float
    requires_approval: bool = True
    created_by_user_id: str


class SuspiciousActivityEvent(DomainEvent):
    """Event fired when suspicious activity is detected"""

    event_type: str = "security.suspicious_activity"
    account_id: str
    transaction_id: Optional[str] = None
    activity_type: str
    risk_score: float
    details: Dict[str, Any] = Field(default_factory=dict)
    requires_investigation: bool = True


class DailyLimitExceededEvent(DomainEvent):
    """Event fired when daily transaction limit is exceeded"""

    event_type: str = "account.daily_limit_exceeded"
    account_id: str
    current_daily_total: float
    daily_limit: float
    attempted_amount: float
    user_id: str


class BulkTransactionCompletedEvent(DomainEvent):
    """Event fired when a bulk transaction operation is completed"""

    event_type: str = "transaction.bulk_completed"
    batch_id: str
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    total_amount: float
    initiated_by_user_id: str


class TransactionReversalEvent(DomainEvent):
    """Event fired when a transaction is reversed"""

    event_type: str = "transaction.reversed"
    original_transaction_id: str
    reversal_transaction_id: str
    account_id: str
    amount: float
    reversal_reason: str
    reversed_by_user_id: str


class MonthlyStatementGeneratedEvent(DomainEvent):
    """Event fired when monthly statement is generated"""

    event_type: str = "statement.monthly_generated"
    account_id: str
    statement_id: str
    period_start: datetime
    period_end: datetime
    transaction_count: int
    total_credits: float
    total_debits: float
    closing_balance: float
