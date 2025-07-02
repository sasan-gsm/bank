from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import registry
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy import event
from ..core.config import settings
from typing import AsyncGenerator

mapper_registry = registry()
Base = mapper_registry.generate_base()


class DatabaseManager:
    def __init__(self) -> None:
        self.engine = create_async_engine(
            url=settings.database_url,
            echo=settings.debug,
            future=True,
            connect_args={"check_same_thread": False}
            if "sqlite" in settings.database_url
            else {},
        )
        # Enable SQLite
        if "sqlite" in settings.database_url:

            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(db_api, connection_record):
                """Set SQLite pragmas for optimal performance."""
                cursor = db_api.cursor()
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


db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session for dependency injection
    """
    async for session in db_manager.get_session():
        yield session


# Add this alias at the end of session.py
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_db to maintain consistency."""
    async for session in get_db():
        yield session
