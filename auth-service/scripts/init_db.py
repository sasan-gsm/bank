#!/usr/bin/env python3
"""Database initialization script for auth-service.

This script creates the database tables, seeds default roles and permissions,
and creates an initial admin user.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.db.session import db_manager
from app.domain.models import User, Role, Permission, DEFAULT_ROLES, DEFAULT_PERMISSIONS
from app.core.security import security
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create all database tables using existing DatabaseManager."""
    logger.info("Creating database tables...")
    await db_manager.create_tables()
    logger.info("Database tables created successfully")


async def seed_permissions():
    """Seed default permissions."""
    logger.info("Seeding default permissions...")

    async with db_manager.get_session() as db:
        # Check if permissions already exist
        count = await db.scalar(
            select(func.count())
            .select_from(Permission)
            .where(Permission.is_deleted == False)
        )

        if count > 0:
            logger.info(f"Found {count} existing permissions, skipping seed")
            return

        # Create permissions
        for perm_data in DEFAULT_PERMISSIONS:
            permission = Permission(
                name=perm_data["name"], description=perm_data["description"]
            )
            db.add(permission)

        await db.commit()
        logger.info(f"Created {len(DEFAULT_PERMISSIONS)} default permissions")


async def seed_roles():
    """Seed default roles with permissions."""
    logger.info("Seeding default roles...")

    async with db_manager.get_session() as db:
        # Check if roles already exist
        count = await db.scalar(
            select(func.count()).select_from(Role).where(Role.is_deleted == False)
        )

        if count > 0:
            logger.info(f"Found {count} existing roles, skipping seed")
            return

        # Get all permissions for assignment
        permissions = await db.scalars(
            select(Permission).where(Permission.is_deleted == False)
        )
        permissions_map = {perm.name: perm.id for perm in permissions}

        # Create default roles
        for role_data in DEFAULT_ROLES:
            role = Role(name=role_data["name"], description=role_data["description"])
            db.add(role)
            await db.flush()  # Get the role ID

            # Assign permissions to role
            for perm_name in role_data["permissions"]:
                if perm_name in permissions_map:
                    stmt = text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"
                    ).bindparams(role_id=role.id, perm_id=permissions_map[perm_name])
                    await db.execute(stmt)

        await db.commit()
        logger.info(f"Created {len(DEFAULT_ROLES)} default roles")


async def create_admin_user():
    """Create initial admin user."""
    logger.info("Creating admin user...")

    admin_email = settings.admin_email or "sasanmehr@gmail.com"
    admin_password = settings.admin_password or "@123"
    admin_username = settings.admin_username or "sassan"

    async with db_manager.get_session() as db:
        # Check if admin user already exists
        count = await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.email == admin_email)
            .where(User.is_deleted == False)
        )

        if count > 0:
            logger.info(
                f"Admin user with email {admin_email} already exists, skipping creation"
            )
            return

        # Create admin user
        hashed_password = security.get_password_hash(admin_password)
        admin_user = User(
            username=admin_username,
            email=admin_email,
            full_name="SysAdmin",
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )

        db.add(admin_user)
        await db.flush()  # Get the user ID

        # Assign admin role
        admin_role_id = await db.scalar(
            select(Role.id).where(Role.name == "admin").where(Role.is_deleted == False)
        )

        if admin_role_id:
            stmt = text(
                "INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"
            ).bindparams(user_id=admin_user.id, role_id=admin_role_id)
            await db.execute(stmt)

        await db.commit()

        logger.info(f"Created admin user: {admin_email}")
        logger.info(f"Admin password: {admin_password}")
        logger.warning("Please change the admin password after first login!")


async def main():
    """Main initialization function."""
    logger.info("Starting database initialization...")

    try:
        # Create tables
        await create_tables()

        # Seed permissions
        await seed_permissions()

        # Seed roles
        await seed_roles()

        # Create admin user
        await create_admin_user()

        logger.info("Database initialization completed successfully!")

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
