# app/core/exceptions.py
from typing import Any, Dict, Optional


class TransactionServiceException(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(TransactionServiceException):
    """Authentication failed."""


class AuthorizationError(TransactionServiceException):
    """Authorization failed."""


class NotFoundError(TransactionServiceException):
    """Generic not-found error."""


class InsufficientBalanceError(TransactionServiceException):
    """Insufficient balance."""


class InvalidTransactionError(TransactionServiceException):
    """Invalid transaction data."""


class AlreadyProcessedError(TransactionServiceException):
    """Transaction is already processed."""


class FutureTransactionError(TransactionServiceException):
    """Future transaction error."""


class DatabaseError(TransactionServiceException):
    """Database operation error."""
