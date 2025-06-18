from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Relationship
from ..db.base import Base
from ..db.mixins import TimestampMixin


class Permission(Base, TimestampMixin):
    __table_name__ = "permissions"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(String, nullable=True)

    # Relationships
    user_permission = Relationship("UserPermission", back_populates="permission")
    user_role = Relationship("UserRole", back_populates="permission")

    def __repr__(self):
        return f"{self.name}"


class UserPermission(Base):
    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(
        Integer, ForeignKey("permission.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, nullable=False)
    # Relationships
    user = Relationship("User", back_populates="user_permissions")
    permission = Relationship("Permission", back_populates="user_permissions")

    __table_args__ = UniqueConstraint(
        "user_id", "permission_id", name="uq_user_permission"
    )
