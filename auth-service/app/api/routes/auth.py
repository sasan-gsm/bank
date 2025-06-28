"""Authentication routes for login, token refresh, and logout."""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_user, get_user_repository
from app.core.security import security
from app.core.config import settings
from app.core.cache import cache_manager
from app.db.session import get_db
from app.db.repository import UserRepository
from app.domain.models import User
from app.streams.events import UserLoginEvent, UserLogoutEvent

router = APIRouter()


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


class LoginResponse(BaseModel):
    """Login response with user info and tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Authenticate user and return access tokens."""
    user_repo = UserRepository(db)
    
    # Try to find user by username or email
    user = await user_repo.get_by_username(form_data.username)
    if not user:
        user = await user_repo.get_by_email(form_data.username)
    
    # Verify user exists and password is correct
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access and refresh tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
    
    token_data = {"user_id": user.id, "username": user.username}
    
    access_token = security.create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    refresh_token = security.create_refresh_token(
        data=token_data,
        expires_delta=refresh_token_expires
    )
    
    # Cache user session
    await cache_manager.set_cache(
        f"user_session:{user.id}",
        {"user_id": user.id, "username": user.username, "login_time": str(user.created_at)},
        ttl=settings.access_token_expire_minutes * 60
    )
    
    # Publish login event
    login_event = UserLoginEvent({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "login_method": "password"
    })
    
    # TODO: Publish event to Redis stream
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_superuser": user.is_superuser,
        }
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        payload = security.verify_token(
            refresh_request.refresh_token, 
            expected_type="refresh"
        )
        user_id = int(payload.get("user_id"))
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        token_data = {"user_id": user.id, "username": user.username}
        
        access_token = security.create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        # Update user session cache
        await cache_manager.set_cache(
            f"user_session:{user.id}",
            {"user_id": user.id, "username": user.username, "refresh_time": str(user.updated_at)},
            ttl=settings.access_token_expire_minutes * 60
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_request.refresh_token,  # Keep the same refresh token
            expires_in=settings.access_token_expire_minutes * 60,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token",
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Logout user and invalidate session."""
    # Remove user session from cache
    await cache_manager.delete_cache(f"user_session:{current_user.id}")
    
    # Invalidate user-related caches
    await cache_manager.invalidate_user_cache(current_user.id)
    
    # Publish logout event
    logout_event = UserLogoutEvent({
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    })
    
    # TODO: Publish event to Redis stream
    
    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get current user information."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "is_superuser": current_user.is_superuser,
        "roles": current_user.get_role_names(),
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


@router.post("/verify-token")
async def verify_token(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Verify if the provided token is valid."""
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "is_active": current_user.is_active,
    }