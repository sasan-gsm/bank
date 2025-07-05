"""User database implementation for FastAPI-Users."""

from typing import Optional
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_session
from app.domain.models import User


class UserDatabase(SQLAlchemyUserDatabase[User, int]):
    """Custom user database with additional methods."""

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        statement = select(User).where(User.username == username)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """Get user database dependency."""
    yield UserDatabase(session, User)