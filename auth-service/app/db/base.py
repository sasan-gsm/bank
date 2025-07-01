from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from typing import Optional

Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    is_deleted: bool = Column(Boolean, default=False, nullable=False)
    deleted_at: Optional[DateTime] = Column(DateTime, nullable=True)


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    __abstract__ = True

    id: int = Column(Integer, primary_key=True, nullable=False)
