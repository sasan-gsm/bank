"""
Pytest configuration and fixtures for transaction service tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.domain.models import Account
from decimal import Decimal


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_transactions.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        yield session

    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(db_session: AsyncSession):
    """Create a test client with database session override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_account(db_session: AsyncSession) -> Account:
    """Create a test account."""
    account = Account(
        account_number="TEST-001",
        account_name="Test Account",
        bank_name="Test Bank",
        current_balance=Decimal("1000.00"),
        available_balance=Decimal("1000.00"),
    )

    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)

    return account


@pytest.fixture
def mock_auth_token():
    """Mock authentication token for testing."""
    return {
        "user_id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "is_superuser": False,
        "permissions": [
            "can_view_transactions",
            "can_create_transactions",
            "can_edit_transactions",
            "can_verify_transactions",
            "can_void_transactions",
            "can_view_bank_balances",
            "can_manage_bank_accounts",
        ],
        "roles": ["accountant"],
    }
