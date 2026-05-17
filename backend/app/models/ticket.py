"""
Ticket and related models — the core domain entities.

Includes ticket comments, attachments, and activity audit log.
Uses pgvector for embedding storage and similarity search.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


# ── Enums ────────────────────────────────────────────────────


class TicketStatus(str, enum.Enum):
    """Ticket lifecycle status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    WAITING_ON_TEAM = "waiting_on_team"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCategory(str, enum.Enum):
    """Ticket category for classification."""

    BILLING = "billing"
    TECHNICAL = "technical"
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    SECURITY = "security"
    ACCOUNT = "account"
    REFUND = "refund"
    GENERAL_INQUIRY = "general_inquiry"


class TicketPriority(str, enum.Enum):
    """Ticket priority/severity level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Ticket ───────────────────────────────────────────────────


class Ticket(BaseModel):
    """Support ticket — the central domain entity."""

    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_category", "category"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_customer_id", "customer_id"),
        Index("ix_tickets_assigned_agent_id", "assigned_agent_id"),
        Index("ix_tickets_assigned_team_id", "assigned_team_id"),
        Index("ix_tickets_created_at", "created_at"),
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ticket_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )

    # Classification
    category: Mapped[TicketCategory | None] = mapped_column(
        Enum(TicketCategory, name="ticket_category", native_enum=True),
        nullable=True,
    )
    predicted_category: Mapped[TicketCategory | None] = mapped_column(
        Enum(TicketCategory, name="ticket_category", native_enum=True, create_constraint=False),
        nullable=True,
    )
    category_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Priority
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority", native_enum=True),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )
    predicted_priority: Mapped[TicketPriority | None] = mapped_column(
        Enum(TicketPriority, name="ticket_priority", native_enum=True, create_constraint=False),
        nullable=True,
    )
    priority_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", native_enum=True),
        default=TicketStatus.OPEN,
        nullable=False,
    )

    # Assignment
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Metadata
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, default="web")
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # AI-generated content
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Vector embedding for semantic search
    embedding = mapped_column(Vector(1536), nullable=True)

    # SLA tracking
    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_breach_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Triage processing flag
    is_triaged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triage_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    customer_user = relationship(
        "User",
        back_populates="created_tickets",
        foreign_keys=[customer_id],
        lazy="selectin",
    )
    assigned_team_rel = relationship(
        "Team",
        back_populates="tickets",
        foreign_keys=[assigned_team_id],
        lazy="selectin",
    )
    assigned_agent_user = relationship(
        "User",
        back_populates="assigned_tickets",
        foreign_keys=[assigned_agent_id],
        lazy="selectin",
    )
    comments = relationship(
        "TicketComment",
        back_populates="ticket",
        order_by="TicketComment.created_at",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    attachments = relationship(
        "TicketAttachment",
        back_populates="ticket",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    activities = relationship(
        "TicketActivity",
        back_populates="ticket",
        order_by="TicketActivity.created_at.desc()",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Ticket {self.ticket_number}: {self.title[:50]}>"


# ── Comment ──────────────────────────────────────────────────


class TicketComment(BaseModel):
    """Comment on a ticket — supports internal notes and customer-facing replies."""

    __tablename__ = "ticket_comments"
    __table_args__ = (Index("ix_ticket_comments_ticket_id", "ticket_id"),)

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    user = relationship("User", back_populates="comments", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TicketComment ticket={self.ticket_id} by={self.user_id}>"


# ── Attachment ───────────────────────────────────────────────


class TicketAttachment(BaseModel):
    """File attachment on a ticket."""

    __tablename__ = "ticket_attachments"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<TicketAttachment {self.original_filename}>"


# ── Activity / Audit Log ─────────────────────────────────────


class TicketActivity(BaseModel):
    """Audit log entry for ticket state changes."""

    __tablename__ = "ticket_activities"
    __table_args__ = (
        Index("ix_ticket_activities_ticket_id", "ticket_id"),
        Index("ix_ticket_activities_created_at", "created_at"),
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="activities")
    user = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TicketActivity {self.action} on {self.ticket_id}>"
