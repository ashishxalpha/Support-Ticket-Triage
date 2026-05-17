"""
Ticket service — core business logic for ticket lifecycle management.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.ticket import (
    Ticket,
    TicketActivity,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketPriority,
    TicketStatus,
)
from app.models.user import User, UserRole
from app.repositories.ticket import TicketRepository
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.ticket import (
    CommentCreate,
    TicketCreate,
    TicketFilter,
    TicketListItem,
    TicketResponse,
    TicketUpdate,
)

logger = get_logger("ticket_service")


class TicketService:
    """Business logic for support ticket management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ticket_repo = TicketRepository(db)

    async def create_ticket(self, data: TicketCreate, customer: User) -> Ticket:
        """Create a new support ticket and enqueue AI triage."""
        ticket_number = await self.ticket_repo.generate_ticket_number()

        ticket = Ticket(
            ticket_number=ticket_number,
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            customer_id=customer.id,
            tags=data.tags or [],
            source=data.source,
            status=TicketStatus.OPEN,
        )
        ticket = await self.ticket_repo.create(ticket)

        # Log creation activity
        await self._log_activity(
            ticket_id=ticket.id,
            user_id=customer.id,
            action="ticket_created",
        )

        logger.info(
            "Ticket created",
            ticket_id=str(ticket.id),
            ticket_number=ticket_number,
            customer_id=str(customer.id),
        )

        return ticket

    async def get_ticket(self, ticket_id: uuid.UUID, user: User) -> Ticket:
        """Get a single ticket with authorization check."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundException("Ticket", ticket_id)

        # Customers can only see their own tickets
        if user.role == UserRole.CUSTOMER and ticket.customer_id != user.id:
            raise ForbiddenException("You can only view your own tickets")

        return ticket

    async def list_tickets(
        self,
        filters: TicketFilter,
        pagination: PaginationParams,
        user: User,
    ) -> PaginatedResponse[TicketListItem]:
        """List tickets with filters, pagination, and role-based scoping."""
        # Customers only see their own tickets
        if user.role == UserRole.CUSTOMER:
            filters.customer_id = user.id

        tickets, total = await self.ticket_repo.list_tickets(
            filters=filters,
            offset=pagination.offset,
            limit=pagination.limit,
        )

        items = [self._to_list_item(t) for t in tickets]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def update_ticket(
        self,
        ticket_id: uuid.UUID,
        data: TicketUpdate,
        user: User,
    ) -> Ticket:
        """Update ticket fields with activity logging."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundException("Ticket", ticket_id)

        # Customers can only update their own tickets (limited fields)
        if user.role == UserRole.CUSTOMER and ticket.customer_id != user.id:
            raise ForbiddenException("You can only update your own tickets")

        update_data = data.model_dump(exclude_unset=True)

        # Log each field change
        for field, new_value in update_data.items():
            old_value = getattr(ticket, field, None)
            if old_value != new_value:
                old_str = old_value.value if hasattr(old_value, "value") else str(old_value)
                new_str = new_value.value if hasattr(new_value, "value") else str(new_value)
                await self._log_activity(
                    ticket_id=ticket_id,
                    user_id=user.id,
                    action="field_updated",
                    field_name=field,
                    old_value=old_str,
                    new_value=new_str,
                )

        # Handle status transitions
        if data.status and data.status != ticket.status:
            if data.status == TicketStatus.RESOLVED:
                update_data["resolved_at"] = datetime.now(timezone.utc)
            if data.status == TicketStatus.IN_PROGRESS and not ticket.first_response_at:
                update_data["first_response_at"] = datetime.now(timezone.utc)

        updated = await self.ticket_repo.update(ticket_id, **update_data)
        if not updated:
            raise NotFoundException("Ticket", ticket_id)

        logger.info(
            "Ticket updated",
            ticket_id=str(ticket_id),
            fields=list(update_data.keys()),
            user_id=str(user.id),
        )

        return updated

    async def add_comment(
        self,
        ticket_id: uuid.UUID,
        data: CommentCreate,
        user: User,
    ) -> TicketComment:
        """Add a comment to a ticket."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundException("Ticket", ticket_id)

        # Customers can only add non-internal comments to their tickets
        if user.role == UserRole.CUSTOMER:
            if ticket.customer_id != user.id:
                raise ForbiddenException("You can only comment on your own tickets")
            data.is_internal = False

        comment = TicketComment(
            ticket_id=ticket_id,
            user_id=user.id,
            content=data.content,
            is_internal=data.is_internal,
        )
        comment = await self.ticket_repo.add_comment(comment)

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            user_id=user.id,
            action="comment_added",
            metadata_json={"is_internal": data.is_internal},
        )

        # Mark first response time if agent is commenting for the first time
        if user.role in (UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER) and not ticket.first_response_at:
            await self.ticket_repo.update(
                ticket_id, first_response_at=datetime.now(timezone.utc)
            )

        logger.info(
            "Comment added",
            ticket_id=str(ticket_id),
            comment_id=str(comment.id),
            user_id=str(user.id),
        )

        return comment

    async def get_comments(
        self,
        ticket_id: uuid.UUID,
        user: User,
    ) -> list[TicketComment]:
        """Get comments for a ticket with role-based internal note filtering."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundException("Ticket", ticket_id)

        include_internal = user.role != UserRole.CUSTOMER
        return await self.ticket_repo.get_comments(ticket_id, include_internal)

    async def get_activities(
        self,
        ticket_id: uuid.UUID,
        user: User,
    ) -> list[TicketActivity]:
        """Get activity log for a ticket."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundException("Ticket", ticket_id)
        return await self.ticket_repo.get_activities(ticket_id)

    async def bulk_update_status(
        self,
        ticket_ids: list[uuid.UUID],
        status: TicketStatus,
        user: User,
    ) -> int:
        """Bulk update status for multiple tickets."""
        updated = 0
        for ticket_id in ticket_ids:
            try:
                await self.update_ticket(
                    ticket_id,
                    TicketUpdate(status=status),
                    user,
                )
                updated += 1
            except (NotFoundException, ForbiddenException):
                continue
        return updated

    async def assign_ticket(
        self,
        ticket_id: uuid.UUID,
        agent_id: uuid.UUID | None = None,
        team_id: uuid.UUID | None = None,
        user: User | None = None,
    ) -> Ticket:
        """Assign ticket to agent and/or team."""
        update_data: dict = {}
        if agent_id is not None:
            update_data["assigned_agent_id"] = agent_id
        if team_id is not None:
            update_data["assigned_team_id"] = team_id

        if update_data:
            updated = await self.ticket_repo.update(ticket_id, **update_data)
            if not updated:
                raise NotFoundException("Ticket", ticket_id)

            if user:
                await self._log_activity(
                    ticket_id=ticket_id,
                    user_id=user.id,
                    action="ticket_assigned",
                    metadata_json=update_data,
                )

            return updated
        raise NotFoundException("Ticket", ticket_id)

    # ── Private Helpers ──────────────────────────────────────

    async def _log_activity(
        self,
        ticket_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        action: str = "",
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        metadata_json: dict | None = None,
    ) -> None:
        activity = TicketActivity(
            ticket_id=ticket_id,
            user_id=user_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            metadata_json=metadata_json,
        )
        await self.ticket_repo.add_activity(activity)

    @staticmethod
    def _to_list_item(ticket: Ticket) -> TicketListItem:
        from app.schemas.user import UserBrief
        from app.schemas.ticket import TeamResponse

        customer = None
        if ticket.customer_user:
            customer = UserBrief.model_validate(ticket.customer_user)

        agent = None
        if ticket.assigned_agent_user:
            agent = UserBrief.model_validate(ticket.assigned_agent_user)

        team = None
        if ticket.assigned_team_rel:
            team = TeamResponse.model_validate(ticket.assigned_team_rel)

        return TicketListItem(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            title=ticket.title,
            category=ticket.category,
            priority=ticket.priority,
            status=ticket.status,
            customer=customer,
            assigned_agent=agent,
            assigned_team=team,
            is_triaged=ticket.is_triaged,
            sentiment_label=ticket.sentiment_label,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )
