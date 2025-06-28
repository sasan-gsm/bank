"""
Pydantic schemas for request/response validation and serialization.
Uses Pydantic v2 with modern field validators and model configuration.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic import ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(
        None, max_length=100, description="User's full name"
    )

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(..., min_length=8, description="User password")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.

        Args:
            v: Password string

        Returns:
            Validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """
        Validate username format.

        Args:
            v: Username string

        Returns:
            Validated username

        Raises:
            ValueError: If username format is invalid
        """
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, hyphens, and underscores"
            )

        return v.lower()


class UserUpdate(BaseModel):
    """Schema for user updates."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = Field(None)
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserWithPermissions(UserResponse):
    """Schema for user response with permissions and roles."""

    permissions: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)


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

    permission_names: List[str] = Field(
        default_factory=list, description="List of permission names"
    )


class RoleUpdate(BaseModel):
    """Schema for role updates."""

    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    permission_names: Optional[List[str]] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(RoleBase):
    """Schema for role response."""

    id: int
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OTPBase(BaseModel):
    """Base OTP schema."""

    purpose: str = Field(..., max_length=50, description="OTP purpose")

    model_config = ConfigDict(from_attributes=True)


class OTPCreate(OTPBase):
    """Schema for OTP creation."""

    user_id: int = Field(..., description="User ID")
    code: str = Field(..., min_length=4, max_length=10, description="OTP code")


class OTPVerify(BaseModel):
    """Schema for OTP verification."""

    email: EmailStr = Field(..., description="User email")
    code: str = Field(..., min_length=4, max_length=10, description="OTP code")
    purpose: str = Field(..., max_length=50, description="OTP purpose")

    model_config = ConfigDict(from_attributes=True)


class OTPResponse(OTPBase):
    """Schema for OTP response."""

    id: int
    user_id: int
    is_used: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User email")

    model_config = ConfigDict(from_attributes=True)


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    email: EmailStr = Field(..., description="User email")
    otp_code: str = Field(..., min_length=4, max_length=10, description="OTP code")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v

    model_config = ConfigDict(from_attributes=True)


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v

    model_config = ConfigDict(from_attributes=True)


class UserRoleAssignment(BaseModel):
    """Schema for user role assignment."""

    user_id: int = Field(..., description="User ID")
    role_names: List[str] = Field(..., description="List of role names to assign")

    model_config = ConfigDict(from_attributes=True)


class UserPermissionAssignment(BaseModel):
    """Schema for user permission assignment."""

    user_id: int = Field(..., description="User ID")
    permission_names: List[str] = Field(
        ..., description="List of permission names to assign"
    )

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Schema for generic message response."""

    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Operation success status")

    model_config = ConfigDict(from_attributes=True)
