"""
WebSocket endpoint for real-time ticket updates and notifications.
"""

from __future__ import annotations

import asyncio
import json
import uuid

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
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("WebSocket connected", user_id=user_id)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                self.active_connections.pop(user_id, None)
        logger.info("WebSocket disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, data: dict) -> None:
        # We can still keep this for server-side push without pubsub, though we use pubsub.
        if user_id in self.active_connections:
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass

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
                        await websocket.send_json(data)
                    except Exception:
                        pass

        redis_task = asyncio.create_task(listen_redis())

        try:
            while True:
                data = await websocket.receive_text()
                # Handle client messages (e.g., subscribe to specific ticket channels)
                try:
                    msg = json.loads(data)
                    action = msg.get("action")
                    if action == "subscribe_ticket":
                        ticket_id = msg.get("ticket_id")
                        if ticket_id:
                            await pubsub.subscribe(f"channel:ticket:{ticket_id}")
                    elif action == "copilot_suggest":
                        # Real-time copilot suggestion triggered by agent typing
                        ticket_id = msg.get("ticket_id")
                        content = msg.get("content", "")
                        if ticket_id and content:
                            # In a real app, dispatch to Celery or call AI directly
                            # For now we'll publish a dummy immediate response to test the pipe
                            asyncio.create_task(_handle_copilot_suggestion(ticket_id, content))
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            pass
        finally:
            redis_task.cancel()
            await pubsub.unsubscribe()
            await pubsub.close()
    finally:
        manager.disconnect(user_id, websocket)

async def _handle_copilot_suggestion(ticket_id: str, content: str) -> None:
    """Handle generating a real-time suggestion."""
    from app.services.realtime import RealtimeService
    from app.ai.factory import get_ai_provider
    provider = get_ai_provider()
    
    try:
        # Ask AI to complete or suggest based on current content
        prompt = f"The agent is typing: '{content}'. Suggest a polite, helpful completion or next sentence."
        response = await provider.generate_response(title="Live Typing", description=prompt, category="general", priority="medium", similar_tickets="")
        
        await RealtimeService.publish_ticket_update(
            ticket_id=uuid.UUID(ticket_id),
            event_type="copilot_suggestion",
            data={"suggestion": response.response}
        )
    except Exception as e:
        logger.error(f"Copilot suggestion failed: {e}")
