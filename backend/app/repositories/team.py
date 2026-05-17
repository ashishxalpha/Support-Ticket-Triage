"""
Team repository — data access for teams and memberships.
"""

from __future__ import annotations

import uuid

from slugify import slugify
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team, TeamMember


class TeamRepository:
    """Data access for Team entities."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, team_id: uuid.UUID) -> Team | None:
        result = await self.db.execute(
            select(Team)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
            .where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Team | None:
        result = await self.db.execute(select(Team).where(Team.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Team | None:
        result = await self.db.execute(
            select(Team).where(func.lower(Team.name) == name.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, description: str | None = None, color: str | None = None) -> Team:
        team = Team(
            name=name,
            slug=slugify(name),
            description=description,
            color=color or "#6366f1",
        )
        self.db.add(team)
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def update(self, team_id: uuid.UUID, **kwargs: object) -> Team | None:
        if "name" in kwargs and kwargs["name"]:
            kwargs["slug"] = slugify(str(kwargs["name"]))
        await self.db.execute(
            update(Team).where(Team.id == team_id).values(**kwargs)
        )
        await self.db.flush()
        return await self.get_by_id(team_id)

    async def list_teams(
        self, is_active: bool | None = None, offset: int = 0, limit: int = 50
    ) -> tuple[list[Team], int]:
        query = select(Team).options(
            selectinload(Team.members).selectinload(TeamMember.user)
        )
        count_query = select(func.count(Team.id))

        if is_active is not None:
            query = query.where(Team.is_active == is_active)
            count_query = count_query.where(Team.is_active == is_active)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.db.execute(
            query.order_by(Team.name).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def add_member(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
    ) -> TeamMember:
        member = TeamMember(team_id=team_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def remove_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if member:
            await self.db.delete(member)
            await self.db.flush()

    async def get_team_for_category(self, category: str) -> Team | None:
        """Get the appropriate team for a ticket category based on naming conventions."""
        category_team_map = {
            "billing": "billing",
            "technical": "platform",
            "bug": "platform",
            "feature_request": "platform",
            "security": "security",
            "account": "customer-success",
            "refund": "billing",
            "general_inquiry": "customer-success",
        }
        slug = category_team_map.get(category.lower())
        if slug:
            return await self.get_by_slug(slug)
        return None
