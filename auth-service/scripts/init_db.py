#!/usr/bin/env python3
"""
Database initialization script for auth-service.

Creates tables, seeds default permissions and roles, and sets up initial admin user.
"""

import asyncio
import sys
from pathlib import Path
import logging

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import db_manager
from app.domain.models import User, Role, Permission, DEFAULT_ROLES, DEFAULT_PERMISSIONS
from app.core.security import security

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_tables():
    logger.info("Creating database tables...")
    await db_manager.create_tables()
    logger.info("Database tables created successfully")


async def seed_permissions():
    logger.info("Seeding default permissions...")
    async with db_manager.get_session() as db:
        existing = await db.scalar(
            select(func.count())
            .select_from(Permission)
            .where(Permission.is_deleted.is_(False))
        )
        if existing:
            logger.info(f"Found {existing} existing permissions, skipping seed")
            return

        perms = [Permission(**p) for p in DEFAULT_PERMISSIONS]
        db.add_all(perms)
        await db.commit()
        logger.info(f"Created {len(perms)} default permissions")


async def seed_roles():
    logger.info("Seeding default roles...")
    async with db_manager.get_session() as db:
        existing = await db.scalar(
            select(func.count()).select_from(Role).where(Role.is_deleted.is_(False))
        )
        if existing:
            logger.info(f"Found {existing} existing roles, skipping seed")
            return

        perms = (
            await db.scalars(select(Permission).where(Permission.is_deleted.is_(False)))
        ).all()
        perms_by_name = {p.name: p for p in perms}

        for role_data in DEFAULT_ROLES:
            role = Role(name=role_data["name"], description=role_data["description"])
            for perm_name in role_data["permissions"]:
                perm = perms_by_name.get(perm_name)
                if perm:
                    role.permissions.append(perm)
            db.add(role)

        await db.commit()
        logger.info(f"Created {len(DEFAULT_ROLES)} default roles")


async def create_admin_user():
    logger.info("Creating admin user...")
    admin_email = settings.admin_email or "sasanmehr@gmail.com"
    admin_password = settings.admin_password or "@123"
    admin_username = settings.admin_username or "sassan"

    async with db_manager.get_session() as db:
        existing = await db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.email == admin_email,
                User.is_deleted.is_(False),
            )
        )
        if existing:
            logger.info(f"Admin user {admin_email} already exists, skipping creation")
            return

        hashed = security.get_password_hash(admin_password)
        admin = User(
            username=admin_username,
            email=admin_email,
            full_name="SysAdmin",
            hashed_password=hashed,
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )

        admin_role = await db.scalar(
            select(Role).where(Role.name == "admin", Role.is_deleted.is_(False))
        )
        if admin_role:
            admin.roles.append(admin_role)  # ORM-managed many-to-many

        db.add(admin)
        await db.commit()

        logger.info(f"Created admin user: {admin_email}")
        logger.info(f"Admin password: {admin_password}")
        logger.warning("Please change the admin password after first login!")


async def main():
    logger.info("Starting database initialization...")
    try:
        await create_tables()
        await seed_permissions()
        await seed_roles()
        await create_admin_user()
        logger.info("Database initialization completed successfully!")
    except Exception:
        logger.exception("Database initialization failed")
        raise


if __name__ == "__main__":
    asyncio.run(main())
