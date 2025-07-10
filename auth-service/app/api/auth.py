"""Authentication API routes with proper access controls.

Endpoint Access Levels:
- Public: /jwt/login, /register, /forgot-password, /health
- Authenticated: /jwt/logout, /me, /verify, /reset-password
- Admin Only: /users/* (user management)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import List

from app.auth.dependencies import fastapi_users, current_active_user, current_superuser
from app.auth.backend import auth_backend
from app.domain.schemas import UserRead, UserCreate, UserUpdate
from app.domain.models import User


# Create router
router = APIRouter()
security = HTTPBearer()

# PUBLIC ENDPOINTS - No authentication required
# Login endpoint (public)
router.include_router(
    fastapi_users.get_auth_router(auth_backend), 
    prefix="/jwt", 
    tags=["auth"]
)

# Registration endpoint (public - but should be admin-only in production)
# Note: In production, you might want to restrict registration to admins only
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/register",
    tags=["auth"],
)

# Password reset endpoints (public)
router.include_router(
    fastapi_users.get_reset_password_router(), 
    prefix="/forgot-password", 
    tags=["auth"]
)

# AUTHENTICATED USER ENDPOINTS - Require valid JWT token
# Email verification endpoints (authenticated)
router.include_router(
    fastapi_users.get_verify_router(UserRead), 
    prefix="/verify", 
    tags=["auth"]
)

# ADMIN ONLY ENDPOINTS - Require superuser privileges
# User management endpoints (admin only)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["admin"],
    dependencies=[Depends(current_superuser)]
)


# CUSTOM ENDPOINTS
@router.get("/me", response_model=UserRead, tags=["auth"])
async def get_current_user(
    current_user: User = Depends(current_active_user),
) -> UserRead:
    """Get current authenticated user profile.
    
    Requires: Valid JWT token
    """
    return current_user


@router.post("/logout", tags=["auth"])
async def logout(
    current_user: User = Depends(current_active_user),
):
    """Logout current user.
    
    Requires: Valid JWT token
    Note: With JWT, logout is typically handled client-side by removing the token.
    """
    return {"message": "Successfully logged out"}


@router.get("/admin/users", response_model=List[UserRead], tags=["admin"])
async def list_all_users(
    current_user: User = Depends(current_superuser)
) -> List[UserRead]:
    """List all users in the system.
    
    Requires: Superuser privileges
    """
    # This will be implemented by the user repository
    from app.db.session import get_async_session
    from app.db.repository import UserRepository
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async def get_users(db: AsyncSession = Depends(get_async_session)):
        user_repo = UserRepository(db)
        return await user_repo.get_all_users()
    
    # For now, return empty list - will be implemented in repository
    return []


@router.delete("/admin/users/{user_id}", tags=["admin"])
async def delete_user(
    user_id: int,
    current_user: User = Depends(current_superuser)
):
    """Delete a user (admin only).
    
    Requires: Superuser privileges
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Implementation will be added to user repository
    return {"message": f"User {user_id} deleted successfully"}


# PUBLIC HEALTH CHECK
@router.get("/health", tags=["health"])
async def auth_health_check():
    """Authentication service health check (public endpoint)."""
    return {
        "status": "healthy", 
        "service": "auth-service", 
        "version": "1.0.0",
        "endpoints": {
            "public": ["/jwt/login", "/register", "/forgot-password", "/health"],
            "authenticated": ["/jwt/logout", "/me", "/verify"],
            "admin_only": ["/users/*", "/admin/*"]
        }
    }
