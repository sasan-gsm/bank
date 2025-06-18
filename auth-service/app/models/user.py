from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Relationship
from ..db.base import Base
from ..db.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __table_name__ = "users"

    id = Column(Integer, primary_key=True)
    user_name = Column(String, unique=True)
    fullname = Column(String, nullable=True)
    email = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)
    # Relationships
    user_role = Relationship("UserRole", back_populates="user")
    user_permission = Relationship("UserPermission", back_populates="user")

    def __repr__(self):
        return f"{self.user_name}"
