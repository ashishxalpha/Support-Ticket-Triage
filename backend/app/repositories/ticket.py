"""
Ticket repository — data access for tickets, comments, attachments, and activities.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import (
    Ticket,
    TicketActivity,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketPriority,
    TicketStatus,
)
from app.schemas.ticket import TicketFilter


class TicketRepository:
    """Data access for Ticket entities and related models."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Ticket CRUD ──────────────────────────────────────────

    async def get_by_id(self, ticket_id: uuid.UUID) -> Ticket | None:
        result = await self.db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.customer_user),
                selectinload(Ticket.assigned_agent_user),
                selectinload(Ticket.assigned_team_rel),
                selectinload(Ticket.comments).selectinload(TicketComment.user),
                selectinload(Ticket.attachments),
            )
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ticket_number(self, ticket_number: str) -> Ticket | None:
        result = await self.db.execute(
            select(Ticket).where(Ticket.ticket_number == ticket_number)
        )
        return result.scalar_one_or_none()

    async def create(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def update(self, ticket_id: uuid.UUID, **kwargs: object) -> Ticket | None:
        await self.db.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**kwargs)
        )
        await self.db.flush()
        return await self.get_by_id(ticket_id)

    async def list_tickets(
        self,
        filters: TicketFilter,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Ticket], int]:
        query = select(Ticket).options(
            selectinload(Ticket.customer_user),
            selectinload(Ticket.assigned_agent_user),
            selectinload(Ticket.assigned_team_rel),
        )
        count_query = select(func.count(Ticket.id))

        # Apply filters
        conditions = []
        if filters.status:
            conditions.append(Ticket.status == filters.status)
        if filters.category:
            conditions.append(Ticket.category == filters.category)
        if filters.priority:
            conditions.append(Ticket.priority == filters.priority)
        if filters.assigned_team_id:
            conditions.append(Ticket.assigned_team_id == filters.assigned_team_id)
        if filters.assigned_agent_id:
            conditions.append(Ticket.assigned_agent_id == filters.assigned_agent_id)
        if filters.customer_id:
            conditions.append(Ticket.customer_id == filters.customer_id)
        if filters.is_triaged is not None:
            conditions.append(Ticket.is_triaged == filters.is_triaged)
        if filters.date_from:
            conditions.append(Ticket.created_at >= filters.date_from)
        if filters.date_to:
            conditions.append(Ticket.created_at <= filters.date_to)
        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(
                or_(
                    Ticket.title.ilike(search_term),
                    Ticket.description.ilike(search_term),
                    Ticket.ticket_number.ilike(search_term),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Sort
        sort_column = getattr(Ticket, filters.sort_by, Ticket.created_at)
        if filters.sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        result = await self.db.execute(query.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def generate_ticket_number(self) -> str:
        """Generate a sequential ticket number like TKT-0001."""
        result = await self.db.execute(select(func.count(Ticket.id)))
        count = (result.scalar() or 0) + 1
        return f"TKT-{count:05d}"

    # ── Vector Search ────────────────────────────────────────

    async def find_similar(
        self,
        embedding: list[float],
        limit: int = 5,
        threshold: float = 0.75,
        exclude_id: uuid.UUID | None = None,
    ) -> list[tuple[Ticket, float]]:
        """Find similar tickets using cosine similarity on pgvector embeddings."""
        # pgvector cosine distance: 1 - cosine_similarity
        distance_expr = Ticket.embedding.cosine_distance(embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        query = (
            select(Ticket, similarity_expr)
            .where(Ticket.embedding.isnot(None))
            .where((1 - distance_expr) >= threshold)
        )

        if exclude_id:
            query = query.where(Ticket.id != exclude_id)

        query = query.order_by(distance_expr.asc()).limit(limit)

        result = await self.db.execute(query)
        return [(row[0], float(row[1])) for row in result.all()]

    async def update_embedding(
        self, ticket_id: uuid.UUID, embedding: list[float]
    ) -> None:
        await self.db.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(embedding=embedding)
        )
        await self.db.flush()

    # ── Comments ─────────────────────────────────────────────

    async def add_comment(self, comment: TicketComment) -> TicketComment:
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def get_comments(
        self,
        ticket_id: uuid.UUID,
        include_internal: bool = True,
    ) -> list[TicketComment]:
        query = (
            select(TicketComment)
            .options(selectinload(TicketComment.user))
            .where(TicketComment.ticket_id == ticket_id)
        )
        if not include_internal:
            query = query.where(TicketComment.is_internal == False)  # noqa: E712
        query = query.order_by(TicketComment.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── Attachments ──────────────────────────────────────────

    async def add_attachment(self, attachment: TicketAttachment) -> TicketAttachment:
        self.db.add(attachment)
        await self.db.flush()
        await self.db.refresh(attachment)
        return attachment

    # ── Activities ───────────────────────────────────────────

    async def add_activity(self, activity: TicketActivity) -> TicketActivity:
        self.db.add(activity)
        await self.db.flush()
        return activity

    async def get_activities(
        self,
        ticket_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[TicketActivity]:
        query = (
            select(TicketActivity)
            .where(TicketActivity.ticket_id == ticket_id)
            .order_by(TicketActivity.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── Analytics Queries ────────────────────────────────────

    async def count_by_status(self) -> dict[str, int]:
        result = await self.db.execute(
            select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
        )
        return {row[0].value: row[1] for row in result.all()}

    async def count_by_category(self) -> dict[str, int]:
        result = await self.db.execute(
            select(Ticket.category, func.count(Ticket.id))
            .where(Ticket.category.isnot(None))
            .group_by(Ticket.category)
        )
        return {row[0].value: row[1] for row in result.all()}

    async def count_by_priority(self) -> dict[str, int]:
        result = await self.db.execute(
            select(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority)
        )
        return {row[0].value: row[1] for row in result.all()}

    async def avg_resolution_time_hours(self) -> float | None:
        result = await self.db.execute(
            select(
                func.avg(
                    func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600
                )
            ).where(Ticket.resolved_at.isnot(None))
        )
        val = result.scalar()
        return round(float(val), 2) if val else None

    async def avg_first_response_time_hours(self) -> float | None:
        result = await self.db.execute(
            select(
                func.avg(
                    func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600
                )
            ).where(Ticket.first_response_at.isnot(None))
        )
        val = result.scalar()
        return round(float(val), 2) if val else None

    async def tickets_created_per_day(self, days: int = 30) -> list[dict]:
        result = await self.db.execute(
            select(
                func.date_trunc("day", Ticket.created_at).label("day"),
                func.count(Ticket.id).label("count"),
            )
            .where(Ticket.created_at >= func.now() - text(f"interval '{days} days'"))
            .group_by("day")
            .order_by("day")
        )
        return [{"date": str(row[0].date()), "count": row[1]} for row in result.all()]

    async def ai_accuracy_stats(self) -> dict:
        """Calculate how often AI predictions match final human-set values."""
        total = await self.db.execute(
            select(func.count(Ticket.id)).where(Ticket.is_triaged == True)  # noqa: E712
        )
        total_count = total.scalar() or 0

        category_match = await self.db.execute(
            select(func.count(Ticket.id)).where(
                and_(
                    Ticket.is_triaged == True,  # noqa: E712
                    Ticket.predicted_category.isnot(None),
                    Ticket.category.isnot(None),
                    Ticket.predicted_category == Ticket.category,
                )
            )
        )
        category_match_count = category_match.scalar() or 0

        priority_match = await self.db.execute(
            select(func.count(Ticket.id)).where(
                and_(
                    Ticket.is_triaged == True,  # noqa: E712
                    Ticket.predicted_priority.isnot(None),
                    Ticket.predicted_priority == Ticket.priority,
                )
            )
        )
        priority_match_count = priority_match.scalar() or 0

        return {
            "total_triaged": total_count,
            "category_accuracy": (
                round(category_match_count / total_count * 100, 1) if total_count else 0
            ),
            "priority_accuracy": (
                round(priority_match_count / total_count * 100, 1) if total_count else 0
            ),
        }
