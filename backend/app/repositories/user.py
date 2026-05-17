"""
User repository — data access layer for user operations.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    """Data access for User entities."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: uuid.UUID, **kwargs: object) -> User | None:
        await self.db.execute(
            update(User).where(User.id == user_id).values(**kwargs)
        )
        await self.db.flush()
        return await self.get_by_id(user_id)

    async def list_users(
        self,
        role: UserRole | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        query = select(User)
        count_query = select(func.count(User.id))

        if role is not None:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.db.execute(
            query.order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_agents_with_ticket_count(self) -> list[dict]:
        """Get support agents with their assigned ticket counts for workload balancing."""
        from app.models.ticket import Ticket, TicketStatus

        agents_query = (
            select(
                User,
                func.count(Ticket.id).label("ticket_count"),
            )
            .outerjoin(
                Ticket,
                (Ticket.assigned_agent_id == User.id)
                & (Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])),
            )
            .where(User.role.in_([UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]))
            .where(User.is_active == True)  # noqa: E712
            .group_by(User.id)
            .order_by(func.count(Ticket.id).asc())
        )
        result = await self.db.execute(agents_query)
        return [
            {"user": row[0], "ticket_count": row[1]}
            for row in result.all()
        ]

    async def count_by_role(self) -> dict[str, int]:
        result = await self.db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        return {row[0].value: row[1] for row in result.all()}
