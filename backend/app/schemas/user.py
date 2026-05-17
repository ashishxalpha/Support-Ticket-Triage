"""User CRUD schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.models.user import UserRole
from app.schemas.common import BaseSchema


class UserResponse(BaseSchema):
    """Public user representation."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    avatar_url: str | None = None
    phone: str | None = None
    department: str | None = None
    customer_tier: str | None = None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseSchema):
    """Admin user creation."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.CUSTOMER
    is_active: bool = True
    phone: str | None = None
    department: str | None = None
    customer_tier: str | None = "standard"


class UserUpdate(BaseSchema):
    """User profile update."""

    full_name: str | None = None
    phone: str | None = None
    department: str | None = None
    avatar_url: str | None = None
    customer_tier: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None


class UserBrief(BaseSchema):
    """Minimal user info for embedding in other responses."""

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    avatar_url: str | None = None
