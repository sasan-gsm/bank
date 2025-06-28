"""
Database initialization and seeding script for transaction service.
"""

import asyncio
from decimal import Decimal
from sqlalchemy.future import select
from app.db.session import db_manager
from app.domain.models import Account
from app.domain.enums import AccountType, Currency
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def seed_database():
    """Seed database with default accounts and data."""
    try:
        async with db_manager.async_session_factory() as session:
            # Check if accounts already exist
            result = await session.execute(select(Account))
            existing_accounts = result.scalars().all()

            if existing_accounts:
                logger.info("Database already seeded with accounts")
                return

            # Create default accounts
            default_accounts = [
                {
                    "account_number": "ACC-001-MAIN",
                    "account_name": "Main Operating Account",
                    "bank_name": "First National Bank",
                    "account_type": AccountType.CHECKING,
                    "current_balance": Decimal("50000.00"),
                    "available_balance": Decimal("50000.00"),
                    "currency": Currency.USD,
                },
                {
                    "account_number": "ACC-002-SAVINGS",
                    "account_name": "Business Savings Account",
                    "bank_name": "First National Bank",
                    "account_type": AccountType.SAVINGS,
                    "current_balance": Decimal("100000.00"),
                    "available_balance": Decimal("100000.00"),
                    "currency": Currency.USD,
                },
                {
                    "account_number": "ACC-003-INVESTMENT",
                    "account_name": "Investment Account",
                    "bank_name": "Investment Bank Corp",
                    "account_type": AccountType.INVESTMENT,
                    "current_balance": Decimal("250000.00"),
                    "available_balance": Decimal("250000.00"),
                    "currency": Currency.USD,
                },
            ]

            # Create accounts
            for account_data in default_accounts:
                account = Account(**account_data)
                session.add(account)

            await session.commit()
            logger.info(f"Created {len(default_accounts)} default accounts")

    except Exception as e:
        logger.error(f"Failed to seed database: {str(e)}")
        raise


async def main():
    """Main function to run database initialization."""
    logger.info("Initializing transaction service database...")

    # Create tables
    await db_manager.create_tables()
    logger.info("Database tables created")

    # Seed data
    await seed_database()
    logger.info("Database initialization completed")


if __name__ == "__main__":
    asyncio.run(main())
