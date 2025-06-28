"""User management routes for registration, profile updates, and user administration."""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import (
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    require_permissions,
    get_user_repository,
)
from app.db.session import get_db
from app.db.repository import UserRepository, RoleRepository
from app.domain.models import User
from app.domain.schemas import UserCreate, UserUpdate, UserResponse
from app.streams.events import UserCreatedEvent, UserUpdatedEvent, UserDeletedEvent
from app.core.cache import cache_manager

router = APIRouter()


class UserRegistrationRequest(BaseModel):
    """User registration request model."""
    username: str
    email: str
    password: str
    full_name: str


class UserListResponse(BaseModel):
    """User list response with pagination."""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class UserRoleAssignment(BaseModel):
    """User role assignment model."""
    role_ids: List[int]


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserRegistrationRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Register a new user."""
    user_repo = UserRepository(db)
    
    # Check if user already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_user = await user_repo.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user_create = UserCreate(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
    )
    
    user = await user_repo.create(user_create)
    
    # Publish user created event
    user_event = UserCreatedEvent({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "registration_method": "direct"
    })
    
    # TODO: Publish event to Redis stream
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get current user's profile."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
    )


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update current user's profile."""
    user_repo = UserRepository(db)
    
    # Check if email is being changed and is not already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = await user_repo.get_by_email(user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Check if username is being changed and is not already taken
    if user_update.username and user_update.username != current_user.username:
        existing_user = await user_repo.get_by_username(user_update.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update user
    updated_user = await user_repo.update(current_user, user_update)
    
    # Publish user updated event
    user_event = UserUpdatedEvent({
        "user_id": updated_user.id,
        "username": updated_user.username,
        "email": updated_user.email,
        "full_name": updated_user.full_name,
        "updated_fields": list(user_update.model_dump(exclude_unset=True).keys())
    })
    
    # TODO: Publish event to Redis stream
    
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        is_active=updated_user.is_active,
        is_verified=updated_user.is_verified,
        is_superuser=updated_user.is_superuser,
    )


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_permissions("user:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List users with pagination and filtering (requires user:read permission)."""
    user_repo = UserRepository(db)
    
    skip = (page - 1) * size
    
    users = await user_repo.list_all(
        skip=skip,
        limit=size,
        search=search,
        is_active=is_active
    )
    
    total = await user_repo.count(search=search, is_active=is_active)
    pages = (total + size - 1) // size
    
    return UserListResponse(
        users=[
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_superuser=user.is_superuser,
            )
            for user in users
        ],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permissions("user:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get user by ID (requires user:read permission)."""
    user_repo = UserRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_permissions("user:update")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update user by ID (requires user:update permission)."""
    user_repo = UserRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if email is being changed and is not already taken
    if user_update.email and user_update.email != user.email:
        existing_user = await user_repo.get_by_email(user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Check if username is being changed and is not already taken
    if user_update.username and user_update.username != user.username:
        existing_user = await user_repo.get_by_username(user_update.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update user
    updated_user = await user_repo.update(user, user_update)
    
    # Publish user updated event
    user_event = UserUpdatedEvent({
        "user_id": updated_user.id,
        "username": updated_user.username,
        "email": updated_user.email,
        "full_name": updated_user.full_name,
        "updated_by": current_user.id,
        "updated_fields": list(user_update.model_dump(exclude_unset=True).keys())
    })
    
    # TODO: Publish event to Redis stream
    
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        is_active=updated_user.is_active,
        is_verified=updated_user.is_verified,
        is_superuser=updated_user.is_superuser,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_permissions("user:delete")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Delete user by ID (requires user:delete permission)."""
    user_repo = UserRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Delete user (this will be a hard delete since we're removing soft delete)
    await user_repo.delete(user)
    
    # Publish user deleted event
    user_event = UserDeletedEvent({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "deleted_by": current_user.id,
    })
    
    # TODO: Publish event to Redis stream
    
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/roles")
async def assign_user_roles(
    user_id: int,
    role_assignment: UserRoleAssignment,
    current_user: User = Depends(require_permissions("user:update", "role:assign")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Assign roles to user (requires user:update and role:assign permissions)."""
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify all roles exist
    roles = []
    for role_id in role_assignment.role_ids:
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found"
            )
        roles.append(role)
    
    # Assign roles to user
    await user_repo.assign_roles(user, roles)
    
    # Invalidate user cache
    await cache_manager.invalidate_user_cache(user.id)
    
    return {"message": "Roles assigned successfully"}


@router.get("/{user_id}/permissions")
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(require_permissions("user:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get user's effective permissions (requires user:read permission)."""
    user_repo = UserRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    permissions = await user.get_all_permissions()
    
    return {
        "user_id": user.id,
        "username": user.username,
        "permissions": [
            {
                "id": perm.id,
                "name": perm.name,
                "description": perm.description,
            }
            for perm in permissions
        ],
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
            }
            for role in user.roles
        ],
    }