"""Pydantic schemas for request/response validation and serialization.
Uses Pydantic v2 with FastAPI-Users integration.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from fastapi_users import schemas


# FastAPI-Users compatible schemas
class UserRead(schemas.BaseUser[int]):
    """User read schema for FastAPI-Users."""

    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(schemas.BaseUserCreate):
    """User creation schema for FastAPI-Users."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )
    full_name: Optional[str] = Field(
        None, max_length=100, description="User's full name"
    )
    phone: Optional[str] = Field(None, max_length=20, description="User's phone number")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, hyphens, and underscores"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 6:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(schemas.BaseUserUpdate):
    """User update schema for FastAPI-Users."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate username format."""
        if v is not None:
            if not v.replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    "Username can only contain letters, numbers, hyphens, and underscores"
                )
            return v.lower()
        return v


# Role and Permission schemas
class PermissionBase(BaseModel):
    """Base permission schema."""

    name: str = Field(..., max_length=100, description="Permission name")
    description: Optional[str] = Field(
        None, max_length=255, description="Permission description"
    )
    model_config = ConfigDict(from_attributes=True)


class PermissionCreate(PermissionBase):
    """Schema for permission creation."""

    pass


class PermissionResponse(PermissionBase):
    """Schema for permission response."""

    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., max_length=50, description="Role name")
    description: Optional[str] = Field(
        None, max_length=255, description="Role description"
    )
    model_config = ConfigDict(from_attributes=True)


class RoleCreate(RoleBase):
    """Schema for role creation."""

    permission_ids: Optional[List[int]] = Field(
        default_factory=list, description="List of permission IDs to assign to role"
    )


class RoleResponse(RoleBase):
    """Schema for role response."""

    id: int
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionResponse] = Field(
        default_factory=list, description="Role permissions"
    )
    model_config = ConfigDict(from_attributes=True)


class UserWithRoles(UserRead):
    """User schema with roles and permissions."""

    roles: List[RoleResponse] = Field(
        default_factory=list, description="User's assigned roles"
    )
    permissions: List[PermissionResponse] = Field(
        default_factory=list, description="User's effective permissions"
    )
