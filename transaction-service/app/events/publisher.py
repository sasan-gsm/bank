from datetime import datetime, timezone
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from app.core.cache import cache_manager


class DomainEvent(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service_name: str = "transaction-service"
    data: Dict[str, Any]


# Transaction Event Classes
class TransactionCreatedEvent(DomainEvent):
    def __init__(
        self,
        transaction_id: str,
        account_id: int,
        amount: float,
        category: str,
        user_id: int,
    ):
        import uuid

        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="transaction.created",
            data={
                "transaction_id": transaction_id,
                "account_id": account_id,
                "amount": amount,
                "category": category,
                "user_id": user_id,
            },
        )


class TransactionVerifiedEvent(DomainEvent):
    def __init__(self, transaction_id: str, account_id: int, verified_by_user_id: int):
        import uuid

        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="transaction.verified",
            data={
                "transaction_id": transaction_id,
                "account_id": account_id,
                "verified_by_user_id": verified_by_user_id,
            },
        )


class TransactionVoidedEvent(DomainEvent):
    def __init__(self, transaction_id: str, account_id: int, voided_by_user_id: int):
        import uuid

        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="transaction.voided",
            data={
                "transaction_id": transaction_id,
                "account_id": account_id,
                "voided_by_user_id": voided_by_user_id,
            },
        )


class EventPublisher:
    def __init__(self):
        self._queue: List[DomainEvent] = []

    async def add_event(self, event: DomainEvent):
        self._queue.append(event)

    async def publish_events(self):
        r = cache_manager.redis_client
        if not r:
            return

        for e in self._queue:
            await r.xadd(f"{e.event_type}", e.model_dump(), maxlen=1000)

        self._queue.clear()


event_publisher = EventPublisher()
