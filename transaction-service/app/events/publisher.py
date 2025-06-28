# app/events/publisher.py
import uuid
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from app.core.cache import cache_manager


class DomainEvent(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service_name: str = "transaction-service"
    data: Dict[str, Any]


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
