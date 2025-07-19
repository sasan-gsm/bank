from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy import event
from ..core.config import settings
from ..domain.models import Base
import os


class DatabaseManager:
    """Database connection and session management."""

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self._async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def init_db(self):
        """Initialize database connection and create tables."""
        # Ensure data directory exists
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Create async engine
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
        )

        # SQLite specific settings for better performance and reliability
        if "sqlite" in settings.database_url:

            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                """Set SQLite pragmas for better performance and reliability."""
                cursor = dbapi_connection.cursor()
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys=ON")
                # Use WAL mode for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                # Optimize synchronization for better performance
                cursor.execute("PRAGMA synchronous=NORMAL")
                # Increase cache size for better performance
                cursor.execute("PRAGMA cache_size=1000")
                # Store temporary tables in memory
                cursor.execute("PRAGMA temp_store=MEMORY")
                # Set busy timeout to handle concurrent access
                cursor.execute("PRAGMA busy_timeout=30000")
                cursor.close()

        # Create session factory
        self._async_session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create all tables
        await self.create_tables()

    async def create_tables(self):
        """Create all database tables."""
        if not self.engine:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Drop all database tables."""
        if not self.engine:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._async_session_factory:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._async_session_factory()

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self._async_session_factory = None

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self.engine is not None and self._async_session_factory is not None


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session."""
    async for session in db_manager.get_session():
        yield session


# Database lifecycle management
async def startup_db():
    """Initialize database on application startup."""
    await db_manager.init_db()
    print("✅ Database initialized successfully")


async def shutdown_db():
    """Close database connection on application shutdown."""
    await db_manager.close()
    print("✅ Database connection closed")


# Health check function
async def check_db_health() -> bool:
    """Check database health."""
    try:
        if not db_manager.is_initialized:
            return False

        async for session in db_manager.get_session():
            # Simple query to check connection
            result = await session.execute("SELECT 1")
            return result.scalar() == 1
    except Exception:
        return False
