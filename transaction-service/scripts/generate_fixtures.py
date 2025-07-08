"""
Generate test fixtures for transaction service development and testing.
"""

import asyncio
import os
import sys
import random
from datetime import date, timedelta
from decimal import Decimal
from app.db.session import db_manager
from app.domain.models import Account, Transaction, FutureTransaction
from app.domain.enums import (
    TransactionDirection,
    TransactionStatus,
    TransactionCategory,
    FutureTransactionStatus,
    FutureTransactionTrigger,
)
import uuid
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logger = logging.getLogger(__name__)


async def generate_test_transactions(account_id: int, count: int = 50):
    """
    Generate test transactions for an account.

    Args:
        account_id: Account ID to create transactions for
        count: Number of transactions to create
    """
    async with db_manager.async_session_factory() as session:
        transactions = []

        for i in range(count):
            transaction = Transaction(
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                account_id=account_id,
                amount=Decimal(str(random.uniform(10.0, 5000.0))),
                direction=random.choice(
                    [TransactionDirection.CREDIT, TransactionDirection.DEBIT]
                ),
                description=f"Test transaction {i + 1}",
                category=random.choice(list(TransactionCategory)),
                status=random.choice(
                    [
                        TransactionStatus.PENDING,
                        TransactionStatus.VERIFIED,
                        TransactionStatus.PROCESSED,
                    ]
                ),
                created_by_user_id=1,  # Assuming user ID 1 exists
                reference_number=f"REF-{random.randint(1000, 9999)}",
            )
            transactions.append(transaction)

        session.add_all(transactions)
        await session.commit()

        logger.info(f"Generated {count} test transactions for account {account_id}")


async def generate_test_future_transactions(account_id: int, count: int = 20):
    """
    Generate test future transactions for an account.

    Args:
        account_id: Account ID to create future transactions for
        count: Number of future transactions to create
    """
    async with db_manager.async_session_factory() as session:
        future_transactions = []

        for i in range(count):
            due_date = date.today() + timedelta(days=random.randint(1, 365))

            future_transaction = FutureTransaction(
                transaction_id=f"FTX-{uuid.uuid4().hex[:12].upper()}",
                account_id=account_id,
                amount=Decimal(str(random.uniform(100.0, 10000.0))),
                direction=random.choice(
                    [TransactionDirection.CREDIT, TransactionDirection.DEBIT]
                ),
                description=f"Test future transaction {i + 1}",
                category=random.choice(list(TransactionCategory)),
                due_date=due_date,
                trigger_type=random.choice(list(FutureTransactionTrigger)),
                status=FutureTransactionStatus.SCHEDULED,
                created_by_user_id=1,  # Assuming user ID 1 exists
                notification_days="7,3,1",  # Notify 7, 3, and 1 days before
                notification_users="1,2",  # Notify users 1 and 2
            )
            future_transactions.append(future_transaction)

        session.add_all(future_transactions)
        await session.commit()

        logger.info(
            f"Generated {count} test future transactions for account {account_id}"
        )


async def main():
    """Main function to generate test fixtures."""
    logger.info("Generating test fixtures...")

    try:
        # Get existing accounts
        async with db_manager.async_session_factory() as session:
            from sqlalchemy.future import select

            result = await session.execute(select(Account))
            accounts = result.scalars().all()

            if not accounts:
                logger.error("No accounts found. Please run init_db.py first.")
                return

            # Generate transactions for each account
            for account in accounts:
                await generate_test_transactions(account.id, 30)
                await generate_test_future_transactions(account.id, 10)

            logger.info("Test fixtures generated successfully")

    except Exception as e:
        logger.error(f"Failed to generate test fixtures: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
