"""
Database session management with SQLite WAL mode optimization.
Provides async session factory and connection management.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from app.core.config import settings
from .base import Base


class DatabaseManager:
    """Database manager with connection pooling and session management."""

    def __init__(self):
        """Initialize database manager with async engine."""
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
            connect_args={"check_same_thread": False}
            if "sqlite" in settings.database_url
            else {},
        )

        # Enable SQLite WAL mode for better concurrent write performance
        if "sqlite" in settings.database_url:

            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                """Set SQLite pragmas for optimal performance."""
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=1000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # Create async session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with proper lifecycle management.

        Yields:
            AsyncSession: Database session
        """
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables (for testing)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session for dependency injection
    """
    async for session in db_manager.get_session():
        yield session
