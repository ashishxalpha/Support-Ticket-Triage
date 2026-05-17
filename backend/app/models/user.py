"""
User model with role-based access control.

Supports four roles: Admin, Support Manager, Support Agent, Customer.
Passwords are stored as bcrypt hashes — never in plaintext.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    SUPPORT_MANAGER = "support_manager"
    SUPPORT_AGENT = "support_agent"
    CUSTOMER = "customer"


class User(BaseModel):
    """Application user — customers, agents, managers, and admins."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        default=UserRole.CUSTOMER,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_tier: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="standard"
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    team_memberships = relationship("TeamMember", back_populates="user", lazy="selectin")
    created_tickets = relationship(
        "Ticket",
        back_populates="customer_user",
        foreign_keys="Ticket.customer_id",
        lazy="noload",
    )
    assigned_tickets = relationship(
        "Ticket",
        back_populates="assigned_agent_user",
        foreign_keys="Ticket.assigned_agent_id",
        lazy="noload",
    )
    comments = relationship("TicketComment", back_populates="user", lazy="noload")
    notifications = relationship("Notification", back_populates="user", lazy="noload")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
