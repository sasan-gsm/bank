from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Relationship
from ..db.base import Base
from ..db.mixins import TimestampMixin


class Role(Base, TimestampMixin):
    __table_name__ = "permissions"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    # Relationships
    role_permissions = Relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphans"
    )

    def __repr__(self):
        return f"{self.role_name}"


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(
        Integer, ForeignKey("permission.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    role = Relationship("Role", back_populates="role_permissions")
    permission = Relationship("Permission", back_populates="role_permissions")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    user = Relationship("User", back_populates="user_roles")
    role = Relationship("Role", back_populates="user_roles")

    __table_args__ = UniqueConstraint("user_id", "role_id", name="uq_user_role")
