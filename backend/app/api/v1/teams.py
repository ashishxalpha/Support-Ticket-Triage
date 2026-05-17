"""
Team management API endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DBSession, require_admin, require_manager_or_admin
from app.core.exceptions import ConflictException, NotFoundException
from app.models.user import User
from app.repositories.team import TeamRepository
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.ticket import TeamCreate, TeamMemberAdd, TeamResponse, TeamUpdate

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=PaginatedResponse[TeamResponse])
async def list_teams(
    db: DBSession,
    current_user: CurrentUser,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse[TeamResponse]:
    """List all teams."""
    repo = TeamRepository(db)
    teams, total = await repo.list_teams(
        is_active=is_active, offset=(page - 1) * page_size, limit=page_size
    )
    items = [TeamResponse.model_validate(t) for t in teams]
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    data: TeamCreate,
    db: DBSession,
    _: User = Depends(require_admin),
) -> TeamResponse:
    """Create a new team (admin only)."""
    repo = TeamRepository(db)
    existing = await repo.get_by_name(data.name)
    if existing:
        raise ConflictException(f"Team '{data.name}' already exists")
    team = await repo.create(data.name, data.description, data.color)
    return TeamResponse.model_validate(team)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> TeamResponse:
    """Get a team by ID."""
    repo = TeamRepository(db)
    team = await repo.get_by_id(team_id)
    if not team:
        raise NotFoundException("Team", team_id)
    return TeamResponse.model_validate(team)


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    data: TeamUpdate,
    db: DBSession,
    _: User = Depends(require_admin),
) -> TeamResponse:
    """Update a team (admin only)."""
    repo = TeamRepository(db)
    update_data = data.model_dump(exclude_unset=True)
    team = await repo.update(team_id, **update_data)
    if not team:
        raise NotFoundException("Team", team_id)
    return TeamResponse.model_validate(team)


@router.post("/{team_id}/members", response_model=SuccessResponse)
async def add_team_member(
    team_id: uuid.UUID,
    data: TeamMemberAdd,
    db: DBSession,
    _: User = Depends(require_manager_or_admin),
) -> SuccessResponse:
    """Add a member to a team."""
    repo = TeamRepository(db)
    team = await repo.get_by_id(team_id)
    if not team:
        raise NotFoundException("Team", team_id)
    await repo.add_member(team_id, data.user_id, data.role)
    return SuccessResponse(message="Member added to team")


@router.delete("/{team_id}/members/{user_id}", response_model=SuccessResponse)
async def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DBSession,
    _: User = Depends(require_manager_or_admin),
) -> SuccessResponse:
    """Remove a member from a team."""
    repo = TeamRepository(db)
    await repo.remove_member(team_id, user_id)
    return SuccessResponse(message="Member removed from team")
