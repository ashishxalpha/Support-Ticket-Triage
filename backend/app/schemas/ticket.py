"""Ticket schemas — request/response models for the ticket domain."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.ticket import TicketCategory, TicketPriority, TicketStatus
from app.schemas.common import BaseSchema
from app.schemas.user import UserBrief


# ── Team Schemas ─────────────────────────────────────────────


class TeamResponse(BaseSchema):
    """Team response."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    is_active: bool
    color: str | None = None
    created_at: datetime


class TeamCreate(BaseSchema):
    """Team creation."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    color: str | None = "#6366f1"


class TeamUpdate(BaseSchema):
    """Team update."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    color: str | None = None


class TeamMemberAdd(BaseSchema):
    """Add member to team."""

    user_id: uuid.UUID
    role: str = "member"


# ── Comment Schemas ──────────────────────────────────────────


class CommentCreate(BaseSchema):
    """Create a ticket comment."""

    content: str = Field(..., min_length=1, max_length=10000)
    is_internal: bool = False


class CommentResponse(BaseSchema):
    """Ticket comment response."""

    id: uuid.UUID
    ticket_id: uuid.UUID
    user: UserBrief | None = None
    content: str
    is_internal: bool
    is_ai_generated: bool = False
    created_at: datetime


# ── Attachment Schemas ───────────────────────────────────────


class AttachmentResponse(BaseSchema):
    """File attachment response."""

    id: uuid.UUID
    ticket_id: uuid.UUID
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


# ── Activity Schemas ─────────────────────────────────────────


class ActivityResponse(BaseSchema):
    """Ticket activity audit log entry."""

    id: uuid.UUID
    ticket_id: uuid.UUID
    user: UserBrief | None = None
    action: str
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    metadata_json: dict | None = None
    created_at: datetime


# ── Ticket Schemas ───────────────────────────────────────────


class TicketCreate(BaseSchema):
    """Create a new support ticket."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=10, max_length=50000)
    category: TicketCategory | None = None
    priority: TicketPriority = TicketPriority.MEDIUM
    tags: list[str] | None = None
    source: str = "web"


class TicketUpdate(BaseSchema):
    """Update an existing ticket."""

    title: str | None = None
    description: str | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assigned_team_id: uuid.UUID | None = None
    assigned_agent_id: uuid.UUID | None = None
    tags: list[str] | None = None


class TicketResponse(BaseSchema):
    """Full ticket response with relationships."""

    id: uuid.UUID
    ticket_number: str
    title: str
    description: str
    category: TicketCategory | None = None
    predicted_category: TicketCategory | None = None
    category_confidence: float | None = None
    priority: TicketPriority
    predicted_priority: TicketPriority | None = None
    priority_confidence: float | None = None
    status: TicketStatus
    customer: UserBrief | None = None
    assigned_team: TeamResponse | None = None
    assigned_agent: UserBrief | None = None
    tags: list[str] | None = None
    source: str | None = None
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    ai_summary: str | None = None
    ai_response: str | None = None
    ai_confidence: float | None = None
    is_triaged: bool = False
    first_response_at: datetime | None = None
    resolved_at: datetime | None = None
    sla_breach_at: datetime | None = None
    comments: list[CommentResponse] = []
    attachments: list[AttachmentResponse] = []
    created_at: datetime
    updated_at: datetime


class TicketListItem(BaseSchema):
    """Lightweight ticket for list views."""

    id: uuid.UUID
    ticket_number: str
    title: str
    category: TicketCategory | None = None
    priority: TicketPriority
    status: TicketStatus
    customer: UserBrief | None = None
    assigned_agent: UserBrief | None = None
    assigned_team: TeamResponse | None = None
    is_triaged: bool = False
    sentiment_label: str | None = None
    created_at: datetime
    updated_at: datetime


class TicketFilter(BaseSchema):
    """Filter parameters for ticket listing."""

    status: TicketStatus | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    assigned_team_id: uuid.UUID | None = None
    assigned_agent_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    is_triaged: bool | None = None
    search: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


class SimilarTicketResponse(BaseSchema):
    """Similar ticket with similarity score."""

    ticket: TicketListItem
    similarity_score: float
