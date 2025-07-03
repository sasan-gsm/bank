"""
Event publishing for inter-service communication and background task processing.
Implements event-driven architecture with Redis streams and Celery tasks.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from app.core.config import settings
from app.core.cache import cache_manager


class DomainEvent(BaseModel):
    """Base class for all domain events."""

    event_id: str
    event_type: str
    timestamp: datetime
    service_name: str = "auth-service"
    data: Dict[str, Any]
    correlation_id: Optional[str] = None

    def __init__(self, **kwargs):
        if "event_id" not in kwargs:
            kwargs["event_id"] = str(uuid.uuid4())
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.utcnow()
        super().__init__(**kwargs)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserCreatedEvent(DomainEvent):
    """Event published when a user is created."""

    def __init__(self, user_data: Dict[str, Any], **kwargs):
        super().__init__(event_type="user.created", data=user_data, **kwargs)


class UserUpdatedEvent(DomainEvent):
    """Event published when a user is updated."""

    def __init__(self, user_data: Dict[str, Any], **kwargs):
        super().__init__(event_type="user.updated", data=user_data, **kwargs)


class UserDeletedEvent(DomainEvent):
    """Event published when a user is deleted."""

    def __init__(self, user_id: int, **kwargs):
        super().__init__(event_type="user.deleted", data={"user_id": user_id}, **kwargs)


class UserRoleChangedEvent(DomainEvent):
    """Event published when user roles are changed."""

    def __init__(
        self, user_id: int, old_roles: List[str], new_roles: List[str], **kwargs
    ):
        super().__init__(
            event_type="user.roles_changed",
            data={"user_id": user_id, "old_roles": old_roles, "new_roles": new_roles},
            **kwargs,
        )


class UserPermissionChangedEvent(DomainEvent):
    """Event published when user permissions are changed."""

    def __init__(
        self,
        user_id: int,
        old_permissions: List[str],
        new_permissions: List[str],
        **kwargs,
    ):
        super().__init__(
            event_type="user.permissions_changed",
            data={
                "user_id": user_id,
                "old_permissions": old_permissions,
                "new_permissions": new_permissions,
            },
            **kwargs,
        )


class PasswordResetRequestedEvent(DomainEvent):
    """Event published when password reset is requested."""

    def __init__(self, user_id: int, email: str, otp_code: str, **kwargs):
        super().__init__(
            event_type="password.reset_requested",
            data={"user_id": user_id, "email": email, "otp_code": otp_code},
            **kwargs,
        )


class PasswordChangedEvent(DomainEvent):
    """Event published when password is changed."""

    def __init__(self, user_id: int, **kwargs):
        super().__init__(
            event_type="password.changed", data={"user_id": user_id}, **kwargs
        )


class EventPublisher:
    """Event publisher for domain events with Redis streams and Celery integration."""

    def __init__(self):
        """Initialize event publisher."""
        self.pending_events: List[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        """
        Add event to pending events list.

        Args:
            event: Domain event to add
        """
        self.pending_events.append(event)

    async def publish_events(self) -> None:
        """
        Publish all pending events to Redis streams and trigger Celery tasks.
        """
        if not self.pending_events:
            return

        try:
            # Publish to Redis streams for real-time processing
            await self._publish_to_streams()

            # Trigger Celery tasks for background processing
            await self._trigger_celery_tasks()

        except Exception as e:
            # Log error but don't fail the main operation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to publish events: {str(e)}")

        finally:
            # Clear pending events
            self.pending_events.clear()

    async def _publish_to_streams(self) -> None:
        """Publish events to Redis streams."""
        if not cache_manager.redis_client:
            return

        for event in self.pending_events:
            stream_name = f"auth-service:{event.event_type}"
            event_data = event.model_dump()

            await cache_manager.redis_client.xadd(
                stream_name,
                event_data,
                maxlen=1000,  # Keep last 1000 events
            )

    async def _trigger_celery_tasks(self) -> None:
        """Trigger appropriate Celery tasks based on event types."""
        from app.streams.handlers import (
            notify_user_created_task,
            notify_user_updated_task,
            notify_user_deleted_task,
            send_otp_task,
        )

        for event in self.pending_events:
            try:
                if event.event_type == "user.created":
                    notify_user_created_task.delay(event.data)

                elif event.event_type == "user.updated":
                    notify_user_updated_task.delay(event.data)

                elif event.event_type == "user.deleted":
                    notify_user_deleted_task.delay(event.data)

                elif event.event_type == "password.reset_requested":
                    send_otp_task.delay(
                        event.data["email"], event.data["otp_code"], "password_reset"
                    )

            except Exception as e:
                # Log individual task failures but continue
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to trigger task for event {event.event_type}: {str(e)}"
                )


# Global event publisher instance
event_publisher = EventPublisher()
