"""
SQLAlchemy models for User, Role, Permission, and OTP entities.
Implements the database schema with relationships and custom permissions.
"""

from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Text
from sqlalchemy.orm import relationship, Mapped
from app.db.base import BaseModel


# Association tables for many-to-many relationships
user_roles = Table(
    "user_roles",
    BaseModel.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

user_permissions = Table(
    "user_permissions",
    BaseModel.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    BaseModel.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class User(BaseModel):
    """User model with authentication and authorization data."""

    __tablename__ = "users"

    # Basic user information
    username: str = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique username for login",
    )

    email: str = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="User email address",
    )

    full_name: Optional[str] = Column(
        String(100), nullable=True, comment="User's full name"
    )

    hashed_password: str = Column(
        String(255), nullable=False, comment="Argon2 hashed password"
    )

    # User status flags
    is_active: bool = Column(
        Boolean, default=True, nullable=False, comment="User account active status"
    )

    is_superuser: bool = Column(
        Boolean, default=False, nullable=False, comment="Superuser privileges flag"
    )

    is_verified: bool = Column(
        Boolean, default=False, nullable=False, comment="Email verification status"
    )

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary=user_roles, back_populates="users", lazy="selectin"
    )

    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=user_permissions,
        back_populates="users",
        lazy="selectin",
    )

    otps: Mapped[List["OTP"]] = relationship(
        "OTP", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    def has_permission(self, permission_name: str) -> bool:
        """
        Check if user has a specific permission.

        Args:
            permission_name: Name of the permission to check

        Returns:
            True if user has the permission, False otherwise
        """
        # Superuser has all permissions
        if self.is_superuser:
            return True

        # Check direct permissions
        for permission in self.permissions:
            if permission.name == permission_name:
                return True

        # Check role-based permissions
        for role in self.roles:
            for permission in role.permissions:
                if permission.name == permission_name:
                    return True

        return False

    def get_all_permissions(self) -> List[str]:
        """
        Get all permissions for the user (direct + role-based).

        Returns:
            List of permission names
        """
        permissions = set()

        # Add direct permissions
        for permission in self.permissions:
            permissions.add(permission.name)

        # Add role-based permissions
        for role in self.roles:
            for permission in role.permissions:
                permissions.add(permission.name)

        return list(permissions)

    def has_role(self, role_name: str) -> bool:
        """
        Check if user has a specific role.

        Args:
            role_name: Name of the role to check

        Returns:
            True if user has the role, False otherwise
        """
        return any(role.name == role_name for role in self.roles)

    def get_role_names(self) -> List[str]:
        """
        Get all role names for the user.

        Returns:
            List of role names
        """
        return [role.name for role in self.roles]


class Role(BaseModel):
    """Role model for grouping permissions."""

    __tablename__ = "roles"

    name: str = Column(
        String(50), unique=True, index=True, nullable=False, comment="Unique role name"
    )

    description: Optional[str] = Column(
        String(255), nullable=True, comment="Role description"
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User", secondary=user_roles, back_populates="roles", lazy="selectin"
    )

    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"

    def has_permission(self, permission_name: str) -> bool:
        """
        Check if role has a specific permission.

        Args:
            permission_name: Name of the permission to check

        Returns:
            True if role has the permission, False otherwise
        """
        return any(perm.name == permission_name for perm in self.permissions)

    def get_permission_names(self) -> List[str]:
        """
        Get all permission names for this role.

        Returns:
            List of permission names
        """
        return [perm.name for perm in self.permissions]


class Permission(BaseModel):
    """Permission model for fine-grained access control."""

    __tablename__ = "permissions"

    name: str = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique permission name",
    )

    description: Optional[str] = Column(
        String(255), nullable=True, comment="Permission description"
    )

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )

    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_permissions,
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}')>"


class OTP(BaseModel):
    """OTP model for password reset and verification."""

    __tablename__ = "otps"

    user_id: int = Column(
        Integer, ForeignKey("users.id"), nullable=False, comment="User ID for OTP"
    )

    code: str = Column(String(10), nullable=False, comment="OTP code")

    purpose: str = Column(
        String(50),
        nullable=False,
        comment="OTP purpose (password_reset, email_verification, etc.)",
    )

    is_used: bool = Column(
        Boolean, default=False, nullable=False, comment="OTP usage status"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="otps")

    def __repr__(self) -> str:
        return f"<OTP(id={self.id}, user_id={self.user_id}, purpose='{self.purpose}')>"


# Default permissions based on banking transaction requirements
DEFAULT_PERMISSIONS = [
    # Transaction permissions
    {"name": "can_view_transactions", "description": "Can view transactions"},
    {"name": "can_create_transactions", "description": "Can create new transactions"},
    {"name": "can_edit_transactions", "description": "Can edit existing transactions"},
    {"name": "can_verify_transactions", "description": "Can verify transactions"},
    {"name": "can_void_transactions", "description": "Can void/scrap transactions"},
    {
        "name": "can_approve_transactions",
        "description": "Can approve pending transactions",
    },
    # Future transaction permissions
    {
        "name": "can_create_future_transactions",
        "description": "Can create future transactions",
    },
    {
        "name": "can_trigger_manual_transactions",
        "description": "Can manually trigger future transactions",
    },
    {
        "name": "can_schedule_notifications",
        "description": "Can schedule transaction notifications",
    },
    # Bank account permissions
    {"name": "can_view_bank_balances", "description": "Can view bank account balances"},
    {"name": "can_manage_bank_accounts", "description": "Can manage bank accounts"},
    {"name": "can_reconcile_accounts", "description": "Can reconcile bank accounts"},
    # User management permissions
    {"name": "can_view_users", "description": "Can view user list"},
    {"name": "can_create_users", "description": "Can create new users"},
    {"name": "can_edit_users", "description": "Can edit existing users"},
    {"name": "can_delete_users", "description": "Can delete users"},
    {"name": "can_activate_users", "description": "Can activate/deactivate users"},
    # Permission management
    {"name": "can_manage_permissions", "description": "Can manage permissions"},
    {
        "name": "can_assign_permissions",
        "description": "Can assign permissions to users",
    },
    # Role management
    {"name": "can_manage_roles", "description": "Can manage roles"},
    {"name": "can_assign_roles", "description": "Can assign roles to users"},
    # Document permissions
    {"name": "can_view_documents", "description": "Can view documents"},
    {"name": "can_upload_documents", "description": "Can upload documents"},
    {"name": "can_delete_documents", "description": "Can delete documents"},
    {"name": "can_approve_documents", "description": "Can approve documents"},
    # Report permissions
    {"name": "can_view_reports", "description": "Can view reports"},
    {"name": "can_generate_reports", "description": "Can generate new reports"},
    {"name": "can_export_reports", "description": "Can export reports"},
    # Analytics permissions
    {"name": "can_view_analytics", "description": "Can view analytics dashboard"},
    {"name": "can_create_analytics", "description": "Can create custom analytics"},
    # System administration
    {"name": "can_manage_system", "description": "Can manage system settings"},
    {"name": "can_view_audit_logs", "description": "Can view audit logs"},
    {"name": "can_backup_system", "description": "Can perform system backups"},
]

# Default roles with their permissions
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Administrator with full system access",
        "permissions": [
            perm["name"] for perm in DEFAULT_PERMISSIONS
        ],  # All permissions
    },
    {
        "name": "manager",
        "description": "Manager with comprehensive transaction and user management access",
        "permissions": [
            "can_view_transactions",
            "can_create_transactions",
            "can_edit_transactions",
            "can_verify_transactions",
            "can_void_transactions",
            "can_approve_transactions",
            "can_create_future_transactions",
            "can_trigger_manual_transactions",
            "can_schedule_notifications",
            "can_view_bank_balances",
            "can_manage_bank_accounts",
            "can_reconcile_accounts",
            "can_view_users",
            "can_create_users",
            "can_edit_users",
            "can_activate_users",
            "can_assign_roles",
            "can_view_documents",
            "can_upload_documents",
            "can_approve_documents",
            "can_view_reports",
            "can_generate_reports",
            "can_export_reports",
            "can_view_analytics",
            "can_create_analytics",
        ],
    },
    {
        "name": "accountant",
        "description": "Accountant with transaction and reporting access",
        "permissions": [
            "can_view_transactions",
            "can_create_transactions",
            "can_edit_transactions",
            "can_verify_transactions",
            "can_create_future_transactions",
            "can_view_bank_balances",
            "can_reconcile_accounts",
            "can_view_documents",
            "can_upload_documents",
            "can_view_reports",
            "can_generate_reports",
            "can_export_reports",
            "can_view_analytics",
        ],
    },
    {
        "name": "clerk",
        "description": "Clerk with basic transaction entry access",
        "permissions": [
            "can_view_transactions",
            "can_create_transactions",
            "can_create_future_transactions",
            "can_view_documents",
            "can_upload_documents",
            "can_view_reports",
        ],
    },
    {
        "name": "viewer",
        "description": "Viewer with read-only access to transactions and reports",
        "permissions": [
            "can_view_transactions",
            "can_view_bank_balances",
            "can_view_documents",
            "can_view_reports",
            "can_view_analytics",
        ],
    },
]
