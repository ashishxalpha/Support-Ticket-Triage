"""
Real-time notification service using Redis Pub/Sub.

Publishes events that WebSocket connections subscribe to,
enabling live ticket updates and notifications across all workers.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger("realtime")


class RealtimeService:
    """Publishes real-time events via Redis Pub/Sub."""

    CHANNEL_TICKET = "channel:ticket:{ticket_id}"
    CHANNEL_USER = "channel:user:{user_id}"
    CHANNEL_GLOBAL = "channel:global"

    @staticmethod
    async def publish_ticket_update(
        ticket_id: uuid.UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish a ticket update event."""
        redis = await get_redis()
        channel = RealtimeService.CHANNEL_TICKET.format(ticket_id=str(ticket_id))
        payload = json.dumps({
            "type": event_type,
            "ticket_id": str(ticket_id),
            "data": data,
        })
        await redis.publish(channel, payload)
        await redis.publish(RealtimeService.CHANNEL_GLOBAL, payload)
        logger.debug("Published ticket update", ticket_id=str(ticket_id), event=event_type)

    @staticmethod
    async def publish_notification(
        user_id: uuid.UUID,
        notification: dict[str, Any],
    ) -> None:
        """Publish a notification to a specific user."""
        redis = await get_redis()
        channel = RealtimeService.CHANNEL_USER.format(user_id=str(user_id))
        payload = json.dumps({
            "type": "notification",
            "user_id": str(user_id),
            "data": notification,
        })
        await redis.publish(channel, payload)

    @staticmethod
    async def publish_global(event_type: str, data: dict[str, Any]) -> None:
        """Publish a global event to all connected clients."""
        redis = await get_redis()
        payload = json.dumps({"type": event_type, "data": data})
        await redis.publish(RealtimeService.CHANNEL_GLOBAL, payload)
