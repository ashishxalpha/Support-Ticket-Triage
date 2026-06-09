"""
Webhooks API for Omnichannel Ingestion.
"""

from typing import Any
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.ticket import Ticket
from app.repositories.ticket import TicketRepository
from app.workers.tasks.triage import process_ticket_triage
from app.core.logging import get_logger

logger = get_logger("webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/email/inbound")
async def inbound_email_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Receive inbound emails parsed by an external service (e.g., SendGrid/Mailgun).
    """
    try:
        # Assuming JSON payload for standard webhook integration
        data = await request.json()
        sender_email = data.get("sender") or data.get("from")
        subject = data.get("subject", "No Subject")
        text_body = data.get("text-body") or data.get("body-plain", "")
        
        if not sender_email:
            return {"status": "error", "message": "No sender email found"}

        # Find or create user
        result = await db.execute(select(User).where(User.email == sender_email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Auto-create basic user
            user = User(
                email=sender_email,
                full_name=sender_email.split("@")[0],
                role=UserRole.CUSTOMER,
                is_active=True
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)

        # Create ticket
        ticket_repo = TicketRepository(db)
        ticket_number = await ticket_repo.generate_ticket_number()
        
        ticket = Ticket(
            title=subject[:500],
            description=text_body,
            ticket_number=ticket_number,
            customer_id=user.id,
            source="email"
        )
        
        ticket = await ticket_repo.create(ticket)
        await db.commit()
        
        # Trigger triage
        process_ticket_triage.delay(str(ticket.id))
        
        return {"status": "success", "ticket_id": str(ticket.id)}

    except Exception as e:
        logger.error(f"Failed to process email webhook: {e}")
        return {"status": "error", "message": str(e)}
