from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr]
    full_name: Optional[str]
    is_active: bool = True


class UserCreate(UserBase):
    id: str
    password: str
    is_active: bool = True
    is_superuser: bool = True

    @field_validator("password")
    @classmethod
    def password_validator(cls, value):
        if len(value) < 5:
            raise ValueError("Choose a password with minimum length of five characters")
        return value


class UserUpdate(UserBase):
    password: Optional[str] = None
    full_name: Optional[str] = None
    updated_at: Optional[datetime] = None

    @field_validator("password")
    @classmethod
    def password_validator(cls, value):
        if len(value) < 5:
            raise ValueError("Choose a password with minimum length of five characters")
        return value


class UserInDBBase(BaseModel):
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
