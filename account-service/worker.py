import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional
import json
from datetime import datetime

from core.config import get_settings
from db.session import DatabaseManager
from domain.events import EventPublisher
from services.account_service import AccountService
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


class AccountWorker:
    """Background worker for processing account-related events and tasks."""

    def __init__(self):
        self.db_manager: Optional[DatabaseManager] = None
        self.event_publisher: Optional[EventPublisher] = None
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.tasks = set()

    async def initialize(self):
        """Initialize worker components."""
        try:
            logger.info("Initializing Account Worker...")

            # Initialize database
            self.db_manager = DatabaseManager(settings.database_url)
            await self.db_manager.init_db()
            logger.info("Database initialized")

            # Initialize event publisher
            self.event_publisher = EventPublisher(
                redis_url=settings.redis_url, stream_name=settings.redis_stream_accounts
            )
            await self.event_publisher.connect()
            logger.info("Event publisher connected")

            # Initialize Redis client for stream consumption
            self.redis_client = redis.from_url(
                settings.redis_url, decode_responses=True
            )
            logger.info("Redis client connected")

            logger.info("Account Worker initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize worker: {str(e)}")
            raise

    async def cleanup(self):
        """Cleanup worker resources."""
        logger.info("Cleaning up Account Worker...")

        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        # Close connections
        if self.event_publisher:
            await self.event_publisher.disconnect()

        if self.redis_client:
            await self.redis_client.close()

        if self.db_manager:
            await self.db_manager.close()

        logger.info("Account Worker cleanup complete")

    async def process_transaction_events(self):
        """Process events from transaction service."""
        logger.info("Starting transaction events processor...")

        consumer_group = "account-service"
        consumer_name = "account-worker"
        stream_name = settings.redis_stream_transactions

        try:
            # Create consumer group if it doesn't exist
            try:
                await self.redis_client.xgroup_create(
                    stream_name, consumer_group, id="0", mkstream=True
                )
                logger.info(f"Created consumer group: {consumer_group}")
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
                logger.info(f"Consumer group {consumer_group} already exists")

            while self.running:
                try:
                    # Read from stream
                    messages = await self.redis_client.xreadgroup(
                        consumer_group,
                        consumer_name,
                        {stream_name: ">"},
                        count=10,
                        block=1000,  # 1 second timeout
                    )

                    for stream, msgs in messages:
                        for msg_id, fields in msgs:
                            await self._process_transaction_event(msg_id, fields)

                            # Acknowledge message
                            await self.redis_client.xack(
                                stream_name, consumer_group, msg_id
                            )

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error processing transaction events: {str(e)}")
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            logger.error(f"Transaction events processor failed: {str(e)}")

    async def _process_transaction_event(self, msg_id: str, fields: Dict[str, Any]):
        """Process a single transaction event."""
        try:
            event_type = fields.get("event_type")
            event_data = json.loads(fields.get("data", "{}"))

            logger.info(f"Processing transaction event: {event_type} (ID: {msg_id})")

            if event_type == "transaction_created":
                await self._handle_transaction_created(event_data)
            elif event_type == "transaction_updated":
                await self._handle_transaction_updated(event_data)
            elif event_type == "transaction_deleted":
                await self._handle_transaction_deleted(event_data)
            else:
                logger.warning(f"Unknown transaction event type: {event_type}")

        except Exception as e:
            logger.error(f"Error processing transaction event {msg_id}: {str(e)}")

    async def _handle_transaction_created(self, event_data: Dict[str, Any]):
        """Handle transaction created event."""
        try:
            account_id = event_data.get("account_id")
            amount = event_data.get("amount")
            transaction_type = event_data.get("type")

            if not all([account_id, amount, transaction_type]):
                logger.warning("Incomplete transaction data received")
                return

            # Update account balance
            async with self.db_manager.get_session() as session:
                account_service = AccountService(session, self.event_publisher)

                # Determine if it's a credit or debit
                is_credit = transaction_type.lower() in [
                    "deposit",
                    "credit",
                    "transfer_in",
                ]

                from domain.schemas import BalanceUpdate

                balance_update = BalanceUpdate(
                    amount=abs(float(amount)),
                    is_credit=is_credit,
                    description=f"Transaction: {transaction_type}",
                )

                # Update balance (using system user ID for automated updates)
                await account_service.update_balance(
                    account_id,
                    balance_update,
                    user_id=0,  # System user
                )

                logger.info(
                    f"Updated account {account_id} balance: "
                    f"{'+' if is_credit else '-'}{amount}"
                )

        except Exception as e:
            logger.error(f"Error handling transaction created: {str(e)}")

    async def _handle_transaction_updated(self, event_data: Dict[str, Any]):
        """Handle transaction updated event."""
        # For now, we'll just log this event
        # In a real system, you might need to adjust balances
        logger.info(f"Transaction updated: {event_data}")

    async def _handle_transaction_deleted(self, event_data: Dict[str, Any]):
        """Handle transaction deleted event."""
        # For now, we'll just log this event
        # In a real system, you might need to reverse balance changes
        logger.info(f"Transaction deleted: {event_data}")

    async def process_account_maintenance(self):
        """Perform periodic account maintenance tasks."""
        logger.info("Starting account maintenance processor...")

        while self.running:
            try:
                await self._run_maintenance_tasks()

                # Wait 1 hour before next maintenance cycle
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in account maintenance: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def _run_maintenance_tasks(self):
        """Run maintenance tasks."""
        logger.info("Running account maintenance tasks...")

        try:
            async with self.db_manager.get_session() as session:
                # Example maintenance tasks:

                # 1. Clean up old audit logs (if implemented)
                # 2. Update account statistics
                # 3. Check for dormant accounts
                # 4. Validate data integrity

                # For now, just log that maintenance ran
                logger.info("Account maintenance completed successfully")

        except Exception as e:
            logger.error(f"Maintenance tasks failed: {str(e)}")

    async def process_health_checks(self):
        """Perform periodic health checks."""
        logger.info("Starting health check processor...")

        while self.running:
            try:
                await self._perform_health_checks()

                # Wait 5 minutes before next health check
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health checks: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _perform_health_checks(self):
        """Perform health checks."""
        try:
            # Check database connection
            async with self.db_manager.get_session() as session:
                await session.execute("SELECT 1")

            # Check Redis connection
            await self.redis_client.ping()

            # Log successful health check
            logger.debug("Health checks passed")

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")

    async def start(self):
        """Start the worker."""
        await self.initialize()

        self.running = True
        logger.info("Starting Account Worker tasks...")

        # Start background tasks
        self.tasks.add(asyncio.create_task(self.process_transaction_events()))
        self.tasks.add(asyncio.create_task(self.process_account_maintenance()))
        self.tasks.add(asyncio.create_task(self.process_health_checks()))

        logger.info("Account Worker started successfully")

        # Wait for all tasks to complete
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Worker tasks cancelled")

    async def stop(self):
        """Stop the worker."""
        logger.info("Stopping Account Worker...")
        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        await self.cleanup()
        logger.info("Account Worker stopped")


# Global worker instance
worker = AccountWorker()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    asyncio.create_task(worker.stop())


async def main():
    """Main worker function."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Worker failed: {str(e)}")
        sys.exit(1)
    finally:
        await worker.stop()


if __name__ == "__main__":
    logger.info("Starting Account Service Worker...")
    asyncio.run(main())
