"""
Repository layer providing clean abstractions over database operations.
Implements instance-based repository pattern with comprehensive CRUD operations.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_, func
from app.domain.models import User, Role, Permission, OTP
from app.domain.schemas import UserCreate, UserUpdate, RoleCreate, RoleUpdate, OTPCreate
from app.core.security import security
from app.core.cache import cache_manager


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize user repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID with relationships loaded.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles), selectinload(User.permissions))
            .where(and_(User.id == user_id, User.is_deleted == False))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email with relationships loaded.

        Args:
            email: User email address

        Returns:
            User object or None if not found
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles), selectinload(User.permissions))
            .where(and_(User.email == email, User.is_deleted == False))
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username with relationships loaded.

        Args:
            username: Username

        Returns:
            User object or None if not found
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles), selectinload(User.permissions))
            .where(and_(User.username == username, User.is_deleted == False))
        )
        return result.scalar_one_or_none()

    async def create(self, user_create: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_create: User creation data

        Returns:
            Created user object
        """
        hashed_password = security.get_password_hash(user_create.password)

        user = User(
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        # Invalidate related caches
        await cache_manager.invalidate_user_cache(user.id)

        return user

    async def update(self, user: User, user_update: UserUpdate) -> User:
        """
        Update user information.

        Args:
            user: User object to update
            user_update: Update data

        Returns:
            Updated user object
        """
        update_data = user_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.session.commit()
        await self.session.refresh(user)

        # Invalidate related caches
        await cache_manager.invalidate_user_cache(user.id)

        return user

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """
        List users with optional filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search term for username/email/full_name
            is_active: Filter by active status

        Returns:
            List of user objects
        """
        query = (
            select(User)
            .options(selectinload(User.roles), selectinload(User.permissions))
            .where(User.is_deleted == False)
        )

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                )
            )

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(
        self, search: Optional[str] = None, is_active: Optional[bool] = None
    ) -> int:
        """
        Count users with optional filtering.

        Args:
            search: Search term for username/email/full_name
            is_active: Filter by active status

        Returns:
            Total count of users
        """
        query = select(func.count(User.id)).where(User.is_deleted == False)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                )
            )

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        result = await self.session.execute(query)
        return result.scalar()

    async def delete(self, user: User) -> None:
        """
        Soft delete a user.

        Args:
            user: User object to delete
        """
        user.is_deleted = True
        user.is_active = False

        await self.session.commit()

        # Invalidate related caches
        await cache_manager.invalidate_user_cache(user.id)

    async def assign_roles(self, user: User, role_names: List[str]) -> User:
        """
        Assign roles to a user.

        Args:
            user: User object
            role_names: List of role names to assign

        Returns:
            Updated user object
        """
        # Get roles by names
        result = await self.session.execute(
            select(Role).where(Role.name.in_(role_names))
        )
        roles = result.scalars().all()

        # Clear existing roles and assign new ones
        user.roles.clear()
        user.roles.extend(roles)

        await self.session.commit()
        await self.session.refresh(user)

        # Invalidate related caches
        await cache_manager.invalidate_user_cache(user.id)
        await cache_manager.invalidate_permission_cache(user.id)

        return user

    async def assign_permissions(self, user: User, permission_names: List[str]) -> User:
        """
        Assign direct permissions to a user.

        Args:
            user: User object
            permission_names: List of permission names to assign

        Returns:
            Updated user object
        """
        # Get permissions by names
        result = await self.session.execute(
            select(Permission).where(Permission.name.in_(permission_names))
        )
        permissions = result.scalars().all()

        # Clear existing permissions and assign new ones
        user.permissions.clear()
        user.permissions.extend(permissions)

        await self.session.commit()
        await self.session.refresh(user)

        # Invalidate related caches
        await cache_manager.invalidate_permission_cache(user.id)

        return user


class RoleRepository:
    """Repository for role-related database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize role repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, role_id: int) -> Optional[Role]:
        """
        Get role by ID with permissions loaded.

        Args:
            role_id: Role ID

        Returns:
            Role object or None if not found
        """
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(and_(Role.id == role_id, Role.is_deleted == False))
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Role]:
        """
        Get role by name with permissions loaded.

        Args:
            name: Role name

        Returns:
            Role object or None if not found
        """
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(and_(Role.name == name, Role.is_deleted == False))
        )
        return result.scalar_one_or_none()

    async def create(self, role_create: RoleCreate) -> Role:
        """
        Create a new role with permissions.

        Args:
            role_create: Role creation data

        Returns:
            Created role object
        """
        role = Role(name=role_create.name, description=role_create.description)

        # Assign permissions if provided
        if role_create.permission_names:
            result = await self.session.execute(
                select(Permission).where(
                    Permission.name.in_(role_create.permission_names)
                )
            )
            permissions = result.scalars().all()
            role.permissions.extend(permissions)

        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)

        return role

    async def update(self, role: Role, role_update: RoleUpdate) -> Role:
        """
        Update role information and permissions.

        Args:
            role: Role object to update
            role_update: Update data

        Returns:
            Updated role object
        """
        update_data = role_update.model_dump(exclude_unset=True)

        # Handle permission updates separately
        permission_names = update_data.pop("permission_names", None)

        # Update basic fields
        for field, value in update_data.items():
            setattr(role, field, value)

        # Update permissions if provided
        if permission_names is not None:
            result = await self.session.execute(
                select(Permission).where(Permission.name.in_(permission_names))
            )
            permissions = result.scalars().all()
            role.permissions.clear()
            role.permissions.extend(permissions)

        await self.session.commit()
        await self.session.refresh(role)

        return role

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Role]:
        """
        List all roles with permissions loaded.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of role objects
        """
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def delete(self, role: Role) -> None:
        """
        Soft delete a role.

        Args:
            role: Role object to delete
        """
        role.is_deleted = True
        await self.session.commit()


class PermissionRepository:
    """Repository for permission-related database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize permission repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, permission_id: int) -> Optional[Permission]:
        """
        Get permission by ID.

        Args:
            permission_id: Permission ID

        Returns:
            Permission object or None if not found
        """
        result = await self.session.execute(
            select(Permission).where(
                and_(Permission.id == permission_id, Permission.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Permission]:
        """
        Get permission by name.

        Args:
            name: Permission name

        Returns:
            Permission object or None if not found
        """
        result = await self.session.execute(
            select(Permission).where(
                and_(Permission.name == name, Permission.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, description: Optional[str] = None) -> Permission:
        """
        Create a new permission.

        Args:
            name: Permission name
            description: Permission description

        Returns:
            Created permission object
        """
        permission = Permission(name=name, description=description)

        self.session.add(permission)
        await self.session.commit()
        await self.session.refresh(permission)

        return permission

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Permission]:
        """
        List all permissions.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of permission objects
        """
        result = await self.session.execute(
            select(Permission)
            .where(Permission.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def delete(self, permission: Permission) -> None:
        """
        Soft delete a permission.

        Args:
            permission: Permission object to delete
        """
        permission.is_deleted = True
        await self.session.commit()


class OTPRepository:
    """Repository for OTP-related database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize OTP repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(self, otp_create: OTPCreate) -> OTP:
        """
        Create a new OTP.

        Args:
            otp_create: OTP creation data

        Returns:
            Created OTP object
        """
        otp = OTP(
            user_id=otp_create.user_id, code=otp_create.code, purpose=otp_create.purpose
        )

        self.session.add(otp)
        await self.session.commit()
        await self.session.refresh(otp)

        return otp

    async def get_valid_otp(self, user_id: int, purpose: str) -> Optional[OTP]:
        """
        Get valid (unused) OTP for user and purpose.

        Args:
            user_id: User ID
            purpose: OTP purpose

        Returns:
            OTP object or None if not found
        """
        result = await self.session.execute(
            select(OTP)
            .where(
                and_(
                    OTP.user_id == user_id, OTP.purpose == purpose, OTP.is_used == False
                )
            )
            .order_by(OTP.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def invalidate_user_otps(self, user_id: int, purpose: str) -> None:
        """
        Mark all OTPs for a user and purpose as used.

        Args:
            user_id: User ID
            purpose: OTP purpose
        """
        result = await self.session.execute(
            select(OTP).where(
                and_(
                    OTP.user_id == user_id, OTP.purpose == purpose, OTP.is_used == False
                )
            )
        )
        otps = result.scalars().all()

        for otp in otps:
            otp.is_used = True

        await self.session.commit()

    async def delete_expired_otps(self, expiry_time) -> int:
        """
        Delete OTPs older than expiry time.

        Args:
            expiry_time: Datetime before which OTPs should be deleted

        Returns:
            Number of deleted OTPs
        """
        result = await self.session.execute(
            select(OTP).where(OTP.created_at < expiry_time)
        )
        otps = result.scalars().all()

        count = len(otps)
        for otp in otps:
            await self.session.delete(otp)

        await self.session.commit()
        return count

    async def get_user_otps(
        self,
        user_id: int,
        purpose: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> List[OTP]:
        """
        Get OTPs for a user with optional purpose filtering.

        Args:
            user_id: User ID
            purpose: Optional OTP purpose filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of OTP objects
        """
        query = select(OTP).where(OTP.user_id == user_id)

        if purpose:
            query = query.where(OTP.purpose == purpose)

        query = query.order_by(OTP.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()
