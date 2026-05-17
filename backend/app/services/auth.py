"""
Authentication service — handles login, registration, token refresh.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictException, NotFoundException
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

logger = get_logger("auth_service")
settings = get_settings()


class AuthService:
    """Business logic for authentication and user registration."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: RegisterRequest, role: UserRole = UserRole.CUSTOMER) -> User:
        """Register a new user account."""
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ConflictException("A user with this email already exists")

        user = User(
            email=data.email.lower(),
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=role,
            phone=data.phone,
            department=data.department,
        )
        user = await self.user_repo.create(user)
        logger.info("User registered", user_id=str(user.id), email=user.email, role=role.value)
        return user

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate user and return JWT tokens."""
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise NotFoundException("Invalid email or password")

        if not user.is_active:
            raise NotFoundException("Account is deactivated")

        access_token = create_access_token(user.id, user.role.value)
        refresh_token = create_refresh_token(user.id)

        logger.info("User logged in", user_id=str(user.id), email=user.email)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        """Exchange a valid refresh token for new access + refresh tokens."""
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise ValueError("Not a refresh token")
            user_id = uuid.UUID(payload["sub"])
        except Exception:
            raise NotFoundException("Invalid or expired refresh token")

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise NotFoundException("User not found or inactive")

        access_token = create_access_token(user.id, user.role.value)
        new_refresh = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        """Change user password after verifying current password."""
        if not verify_password(current_password, user.hashed_password):
            raise NotFoundException("Current password is incorrect")

        await self.user_repo.update(user.id, hashed_password=hash_password(new_password))
        logger.info("Password changed", user_id=str(user.id))
