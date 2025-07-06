from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, registry
from datetime import datetime


# Create the base class for all models
mapped_registery = registry()
Base = mapped_registery.generate_base()


class TimestampMixin:
    """Mixin for timestamp fields in database models."""

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )

    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp",
    )


class BaseModel(Base, TimestampMixin):
    """Base model with common fields for all database entities."""

    __abstract__ = True

    id: Mapped[int] = Column(
        Integer, primary_key=True, index=True, comment="Primary key"
    )
