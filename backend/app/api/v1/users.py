"""
User management API endpoints (admin only).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DBSession, require_admin, require_manager_or_admin
from app.core.exceptions import NotFoundException
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.auth import AuthService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    db: DBSession,
    _: User = Depends(require_manager_or_admin),
    role: UserRole | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[UserResponse]:
    """List all users (managers and admins only)."""
    repo = UserRepository(db)
    users, total = await repo.list_users(
        role=role, is_active=is_active, offset=(page - 1) * page_size, limit=page_size
    )
    items = [UserResponse.model_validate(u) for u in users]
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    db: DBSession,
    _: User = Depends(require_admin),
) -> UserResponse:
    """Create a new user (admin only)."""
    from app.schemas.auth import RegisterRequest

    service = AuthService(db)
    register_data = RegisterRequest(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        phone=data.phone,
        department=data.department,
    )
    user = await service.register(register_data, role=data.role)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: DBSession,
    _: User = Depends(require_manager_or_admin),
) -> UserResponse:
    """Get a user by ID."""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundException("User", user_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> UserResponse:
    """Update a user (admin can update anyone, users can update themselves)."""
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("You can only update your own profile")

    repo = UserRepository(db)
    update_data = data.model_dump(exclude_unset=True)

    # Non-admins cannot change their own role or active status
    if current_user.role != UserRole.ADMIN:
        update_data.pop("role", None)
        update_data.pop("is_active", None)

    user = await repo.update(user_id, **update_data)
    if not user:
        raise NotFoundException("User", user_id)
    return UserResponse.model_validate(user)
