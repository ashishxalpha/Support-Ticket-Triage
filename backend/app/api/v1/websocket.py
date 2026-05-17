"""
WebSocket endpoint for real-time ticket updates and notifications.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import get_db_session
from app.core.deps import get_current_user_ws
from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger("websocket")
router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info("WebSocket connected", user_id=user_id)

    def disconnect(self, user_id: str) -> None:
        self.active_connections.pop(user_id, None)
        logger.info("WebSocket disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, data: dict) -> None:
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(user_id)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = "") -> None:
    """WebSocket endpoint with JWT authentication and Redis pub/sub."""
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return

    async for session in get_db_session():
        user = await get_current_user_ws(websocket, session, token)
        break

    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = str(user.id)
    await manager.connect(user_id, websocket)

    try:
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(
            f"channel:user:{user_id}",
            "channel:global",
        )

        async def listen_redis() -> None:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await manager.send_to_user(user_id, data)
                    except Exception:
                        pass

        redis_task = asyncio.create_task(listen_redis())

        try:
            while True:
                data = await websocket.receive_text()
                # Handle client messages (e.g., subscribe to specific ticket channels)
                try:
                    msg = json.loads(data)
                    if msg.get("action") == "subscribe_ticket":
                        ticket_id = msg.get("ticket_id")
                        if ticket_id:
                            await pubsub.subscribe(f"channel:ticket:{ticket_id}")
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            pass
        finally:
            redis_task.cancel()
            await pubsub.unsubscribe()
            await pubsub.close()
    finally:
        manager.disconnect(user_id)
