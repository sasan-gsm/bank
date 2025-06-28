# app/db/base.py
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TimestampMixin:
    """Adds created_at and updated_at."""

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft deletion support."""

    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """Abstract base model with ID, timestamps, and soft delete."""

    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)
