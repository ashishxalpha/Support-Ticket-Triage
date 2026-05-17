"""
Triage Celery tasks — asynchronous AI ticket processing.

All AI operations run as background tasks to avoid blocking API requests.
Each task includes retry logic and error reporting.
"""

from __future__ import annotations

import asyncio
import uuid

from celery import shared_task

from app.core.logging import get_logger

logger = get_logger("triage_tasks")


def _run_async(coro):  # type: ignore
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    name="app.workers.tasks.triage.process_ticket_triage",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_ticket_triage(self, ticket_id: str) -> dict:  # type: ignore
    """
    Run the full AI triage pipeline on a ticket.

    This is the primary background task that processes every new ticket.
    It classifies, predicts priority, summarizes, generates embeddings,
    finds similar tickets, generates a response, and routes the ticket.
    """
    logger.info(
        "Starting triage task",
        ticket_id=ticket_id,
        task_id=self.request.id,
    )

    try:
        result = _run_async(_process_triage(ticket_id))
        logger.info(
            "Triage task completed",
            ticket_id=ticket_id,
            result_keys=list(result.keys()) if isinstance(result, dict) else None,
        )
        # Publish real-time update
        _run_async(_notify_triage_complete(ticket_id, result))
        return result
    except Exception as exc:
        logger.error(
            "Triage task failed",
            ticket_id=ticket_id,
            error=str(exc),
            attempt=self.request.retries + 1,
        )
        raise self.retry(exc=exc)


@shared_task(
    name="app.workers.tasks.triage.generate_embedding",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def generate_embedding_task(self, ticket_id: str) -> dict:  # type: ignore
    """Generate embedding for a single ticket (used for re-embedding)."""
    logger.info("Generating embedding", ticket_id=ticket_id)
    try:
        result = _run_async(_generate_embedding(ticket_id))
        return {"status": "success", "ticket_id": ticket_id}
    except Exception as exc:
        logger.error("Embedding task failed", ticket_id=ticket_id, error=str(exc))
        raise self.retry(exc=exc)


async def _process_triage(ticket_id: str) -> dict:
    """Async triage execution."""
    from app.core.database import async_session_factory
    from app.services.ai_triage import AITriageService

    async with async_session_factory() as session:
        service = AITriageService(session)
        result = await service.triage_ticket(uuid.UUID(ticket_id))
        await session.commit()
        return result


async def _generate_embedding(ticket_id: str) -> None:
    """Async embedding generation."""
    from app.core.database import async_session_factory
    from app.ai.factory import get_ai_provider
    from app.repositories.ticket import TicketRepository

    provider = get_ai_provider()
    async with async_session_factory() as session:
        repo = TicketRepository(session)
        ticket = await repo.get_by_id(uuid.UUID(ticket_id))
        if ticket:
            embed_text = f"{ticket.title}\n\n{ticket.description}"
            result = await provider.generate_embedding(embed_text)
            await repo.update_embedding(ticket.id, result.embedding)
            await session.commit()


async def _notify_triage_complete(ticket_id: str, result: dict) -> None:
    """Send real-time notification after triage completes."""
    try:
        from app.services.realtime import RealtimeService
        await RealtimeService.publish_ticket_update(
            ticket_id=uuid.UUID(ticket_id),
            event_type="triage_complete",
            data=result,
        )
    except Exception as e:
        logger.warning("Failed to publish triage notification", error=str(e))
