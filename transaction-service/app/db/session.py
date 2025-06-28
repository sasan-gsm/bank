# app/db/session.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from app.core.config import settings
from app.db.base import Base


class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
            connect_args={"check_same_thread": False}
            if "sqlite" in settings.database_url
            else {},
        )
        if "sqlite" in settings.database_url:

            @event.listens_for(self.engine.sync_engine, "connect")
            def _on_connect(dbapi_conn, _):
                cur = dbapi_conn.cursor()
                cur.executescript(
                    """
                    PRAGMA journal_mode=WAL;
                    PRAGMA synchronous=NORMAL;
                    PRAGMA cache_size=1000;
                    PRAGMA temp_store=MEMORY;
                    PRAGMA foreign_keys=ON;
                    """
                )
                cur.close()

        self._session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
            except:
                await session.rollback()
                raise

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for s in db_manager.get_session():
        yield s
