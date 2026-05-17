"""
Notification Celery tasks — async notification delivery.
"""

from __future__ import annotations

import asyncio
import uuid

from celery import shared_task

from app.core.logging import get_logger

logger = get_logger("notification_tasks")


def _run_async(coro):  # type: ignore
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    name="app.workers.tasks.notifications.send_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def send_notification(
    self,  # type: ignore
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict | None = None,
    link: str | None = None,
) -> dict:
    """Create a persistent notification and publish via WebSocket."""
    try:
        result = _run_async(
            _create_notification(user_id, notification_type, title, message, data, link)
        )
        return result
    except Exception as exc:
        logger.error("Notification task failed", user_id=user_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(
    name="app.workers.tasks.notifications.send_slack_notification",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def send_slack_notification(
    self,  # type: ignore
    channel: str,
    message: str,
    ticket_id: str | None = None,
) -> dict:
    """Send a notification to Slack (when webhook URL is configured)."""
    from app.core.config import get_settings
    settings = get_settings()

    if not settings.slack_webhook_url:
        logger.info("Slack notification skipped — no webhook URL configured")
        return {"status": "skipped", "reason": "no_webhook_url"}

    try:
        import httpx
        response = httpx.post(
            settings.slack_webhook_url,
            json={
                "channel": channel,
                "text": message,
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message},
                    }
                ],
            },
            timeout=10,
        )
        response.raise_for_status()
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Slack notification failed", error=str(exc))
        raise self.retry(exc=exc)


async def _create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict | None,
    link: str | None,
) -> dict:
    from app.core.database import async_session_factory
    from app.models.notification import Notification
    from app.services.realtime import RealtimeService

    async with async_session_factory() as session:
        notification = Notification(
            user_id=uuid.UUID(user_id),
            type=notification_type,
            title=title,
            message=message,
            data=data,
            link=link,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        # Publish via WebSocket
        await RealtimeService.publish_notification(
            user_id=uuid.UUID(user_id),
            notification={
                "id": str(notification.id),
                "type": notification_type,
                "title": title,
                "message": message,
                "data": data,
                "link": link,
                "created_at": notification.created_at.isoformat(),
            },
        )

        return {"status": "sent", "notification_id": str(notification.id)}
