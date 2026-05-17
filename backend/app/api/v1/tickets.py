"""
Ticket management API endpoints.

Full CRUD with filtering, pagination, comments, attachments,
activity log, and AI triage integration.
"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.config import get_settings
from app.core.deps import CurrentUser, DBSession, require_agent_or_above
from app.core.exceptions import AppException, NotFoundException
from app.models.ticket import TicketAttachment, TicketCategory, TicketPriority, TicketStatus
from app.models.user import User
from app.repositories.ticket import TicketRepository
from app.schemas.common import PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.ticket import (
    ActivityResponse,
    AttachmentResponse,
    CommentCreate,
    CommentResponse,
    SimilarTicketResponse,
    TicketCreate,
    TicketFilter,
    TicketListItem,
    TicketResponse,
    TicketUpdate,
)
from app.services.ticket import TicketService

settings = get_settings()
router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    data: TicketCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> TicketResponse:
    """Create a new support ticket and enqueue AI triage."""
    service = TicketService(db)
    ticket = await service.create_ticket(data, current_user)

    # Enqueue AI triage as background task (best-effort)
    try:
        from app.workers.celery_app import celery_app as _celery

        task = _celery.send_task(
            "app.workers.tasks.triage.process_ticket_triage",
            args=[str(ticket.id)],
            queue="triage",
        )
        repo = TicketRepository(db)
        await repo.update(ticket.id, triage_task_id=task.id)
    except Exception:
        # If broker is unavailable, ticket still gets created.
        # Triage can be retried later.
        pass

    # Re-fetch with all relationships loaded
    repo = TicketRepository(db)
    ticket = await repo.get_by_id(ticket.id)
    return TicketResponse.model_validate(ticket)


@router.get("", response_model=PaginatedResponse[TicketListItem])
async def list_tickets(
    db: DBSession,
    current_user: CurrentUser,
    status: TicketStatus | None = None,
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
    assigned_team_id: uuid.UUID | None = None,
    assigned_agent_id: uuid.UUID | None = None,
    is_triaged: bool | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TicketListItem]:
    """List tickets with filters and pagination."""
    filters = TicketFilter(
        status=status,
        category=category,
        priority=priority,
        assigned_team_id=assigned_team_id,
        assigned_agent_id=assigned_agent_id,
        is_triaged=is_triaged,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    pagination = PaginationParams(page=page, page_size=page_size)
    service = TicketService(db)
    return await service.list_tickets(filters, pagination, current_user)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> TicketResponse:
    """Get a single ticket with full details."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id, current_user)
    return TicketResponse.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: uuid.UUID,
    data: TicketUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> TicketResponse:
    """Update ticket fields."""
    service = TicketService(db)
    ticket = await service.update_ticket(ticket_id, data, current_user)
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    ticket_id: uuid.UUID,
    data: CommentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> CommentResponse:
    """Add a comment to a ticket."""
    service = TicketService(db)
    comment = await service.add_comment(ticket_id, data, current_user)
    return CommentResponse.model_validate(comment)


@router.get("/{ticket_id}/comments", response_model=list[CommentResponse])
async def get_comments(
    ticket_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> list[CommentResponse]:
    """Get comments for a ticket."""
    service = TicketService(db)
    comments = await service.get_comments(ticket_id, current_user)
    return [CommentResponse.model_validate(c) for c in comments]


@router.get("/{ticket_id}/activities", response_model=list[ActivityResponse])
async def get_activities(
    ticket_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> list[ActivityResponse]:
    """Get activity log for a ticket."""
    service = TicketService(db)
    activities = await service.get_activities(ticket_id, current_user)
    return [ActivityResponse.model_validate(a) for a in activities]


@router.post("/{ticket_id}/attachments", response_model=AttachmentResponse, status_code=201)
async def upload_attachment(
    ticket_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> AttachmentResponse:
    """Upload a file attachment to a ticket."""
    # Validate file
    if not file.filename:
        raise AppException("Filename is required", status_code=400)

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.allowed_extensions_set:
        raise AppException(f"File type '.{ext}' is not allowed", status_code=400)

    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise AppException(
            f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
            status_code=400,
        )

    # Save file
    stored_filename = f"{uuid.uuid4()}.{ext}"
    upload_path = os.path.join(settings.upload_dir, str(ticket_id))
    os.makedirs(upload_path, exist_ok=True)
    file_path = os.path.join(upload_path, stored_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create database record
    repo = TicketRepository(db)
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        uploaded_by_id=current_user.id,
        filename=stored_filename,
        original_filename=file.filename,
        file_path=file_path,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
    )
    attachment = await repo.add_attachment(attachment)
    return AttachmentResponse.model_validate(attachment)


@router.get("/{ticket_id}/similar", response_model=list[SimilarTicketResponse])
async def get_similar_tickets(
    ticket_id: uuid.UUID,
    db: DBSession,
    _: User = Depends(require_agent_or_above),
    limit: int = Query(default=5, ge=1, le=20),
) -> list[SimilarTicketResponse]:
    """Find similar tickets using vector search."""
    repo = TicketRepository(db)
    ticket = await repo.get_by_id(ticket_id)
    if not ticket:
        raise NotFoundException("Ticket", ticket_id)

    if ticket.embedding is None:
        return []

    similar = await repo.find_similar(
        embedding=list(ticket.embedding),
        limit=limit,
        threshold=settings.similarity_threshold,
        exclude_id=ticket_id,
    )

    results = []
    for sim_ticket, score in similar:
        list_item = TicketListItem.model_validate(sim_ticket)
        results.append(SimilarTicketResponse(ticket=list_item, similarity_score=score))
    return results


@router.post("/bulk/status", response_model=SuccessResponse)
async def bulk_update_status(
    ticket_ids: list[uuid.UUID],
    status: TicketStatus,
    db: DBSession,
    current_user: CurrentUser,
    _: User = Depends(require_agent_or_above),
) -> SuccessResponse:
    """Bulk update status for multiple tickets."""
    service = TicketService(db)
    updated = await service.bulk_update_status(ticket_ids, status, current_user)
    return SuccessResponse(message=f"Updated {updated} tickets")
