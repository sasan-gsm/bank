"""FastAPI dependencies for authentication, database sessions, and common utilities."""

from typing import Optional, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import security
from app.core.cache import cache_manager
from app.db.session import get_db
from app.db.repository import UserRepository
from app.domain.models import User

# Security scheme for JWT tokens
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    try:
        # Verify JWT token
        payload = security.verify_token(credentials.credentials, expected_type="access")
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
        
        return user
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def require_permissions(*required_permissions: str):
    """Dependency factory for permission-based access control."""
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        """Check if user has required permissions."""
        user_permissions = await current_user.get_all_permissions()
        user_permission_names = {perm.name for perm in user_permissions}
        
        missing_permissions = set(required_permissions) - user_permission_names
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing_permissions)}"
            )
        
        return current_user
    
    return permission_checker


def require_roles(*required_roles: str):
    """Dependency factory for role-based access control."""
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        """Check if user has required roles."""
        user_role_names = current_user.get_role_names()
        
        if not any(role in user_role_names for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}"
            )
        
        return current_user
    
    return role_checker


async def get_user_repository(
    db: AsyncSession = Depends(get_db),
) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(db)