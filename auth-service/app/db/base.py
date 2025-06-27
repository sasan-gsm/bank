"""
SQLAlchemy Base class and common database utilities.
Provides foundation for all database models.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

# Create the base class for all models
Base = declarative_base()


class TimestampMixin:
    """Mixin for timestamp fields in database models."""

    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )

    updated_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp",
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    is_deleted: bool = Column(
        Boolean, default=False, nullable=False, comment="Soft delete flag"
    )

    deleted_at: Optional[datetime] = Column(
        DateTime(timezone=True), nullable=True, comment="Soft delete timestamp"
    )


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """Base model with common fields for all database entities."""

    __abstract__ = True

    id: int = Column(Integer, primary_key=True, index=True, comment="Primary key")
