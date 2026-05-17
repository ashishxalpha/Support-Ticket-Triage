"""
Team and team membership models.

Supports organizational team structure for ticket routing.
Agents can belong to multiple teams.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TeamRole(str, enum.Enum):
    """Role within a team."""

    LEAD = "lead"
    MEMBER = "member"


class Team(BaseModel):
    """Support team that tickets can be routed to."""

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True, default="#6366f1")

    # Relationships
    members = relationship("TeamMember", back_populates="team", lazy="selectin")
    tickets = relationship("Ticket", back_populates="assigned_team_rel", lazy="noload")

    def __repr__(self) -> str:
        return f"<Team {self.name}>"


class TeamMember(BaseModel):
    """Association between users and teams with role information."""

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="uq_team_members_user_team"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[TeamRole] = mapped_column(
        Enum(TeamRole, name="team_role", native_enum=True),
        default=TeamRole.MEMBER,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="team_memberships", lazy="selectin")
    team = relationship("Team", back_populates="members", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TeamMember user={self.user_id} team={self.team_id}>"
