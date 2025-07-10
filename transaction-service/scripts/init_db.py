"""
Database initialization and seeding script for transaction service.
"""

from pathlib import Path
import sys
import asyncio
from decimal import Decimal
from sqlalchemy.future import select
from app.db.session import db_manager
from app.domain.models import Account
import logging

logger = logging.getLogger(__name__)
# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


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
                    "account_number": "0110071588004",
                    "bank_name": "بانک ملی شعبه حافظ",
                    "current_balance": Decimal("0.00"),
                    "available_balance": Decimal("0.00"),
                },
                {
                    "account_number": "2431104758251",
                    "bank_name": "بانک پاسارگاد کاشانی",
                    "current_balance": Decimal("0.00"),
                    "available_balance": Decimal("0.00"),
                },
                {
                    "account_number": "00115368811000",
                    "bank_name": "بانک ملی شعبه حافظ",
                    "current_balance": Decimal("0.00"),
                    "available_balance": Decimal("0.00"),
                },
                {
                    "account_number": "2438104758251",
                    "bank_name": "بانک پاسارگاد کاشانی",
                    "current_balance": Decimal("0.00"),
                    "available_balance": Decimal("0.00"),
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
