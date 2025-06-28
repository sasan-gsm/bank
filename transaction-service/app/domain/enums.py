# app/domain/enums.py

from enum import Enum


class TransactionType(str, Enum):
    DAILY = "daily"
    FUTURE = "future"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    PROCESSED = "processed"
    VOIDED = "voided"
    FAILED = "failed"


class FutureTransactionTrigger(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class FutureTransactionStatus(str, Enum):
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"
    PROCESSED = "processed"
    SCRAPPED = "scrapped"
    EXPIRED = "expired"


class TransactionCategory(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
