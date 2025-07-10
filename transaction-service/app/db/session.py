# app/db/session.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy import event
from app.core.config import settings
from app.db.base import Base
from typing import Optional


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

        # SQLite specific settings
        if "sqlite" in settings.database_url:

            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=1000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()

        self._async_session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    @property
    def async_session_factory(self) -> Optional[AsyncSession]:
        """Get async session factory"""
        return self._async_session_factory

    @property
    def async_session(self) -> Optional[AsyncSession]:
        """Backward compatibility property"""
        return self._async_session_factory

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        if not self._async_session_factory:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        async with self._async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self):
        if not hasattr(self, "engine"):
            raise RuntimeError("Database engine not initialized. Call init_db() first.")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        if not hasattr(self, "engine"):
            raise RuntimeError("Database engine not initialized. Call init_db() first.")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for s in db_manager.get_session():
        yield s
