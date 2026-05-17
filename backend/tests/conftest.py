"""
Test configuration and fixtures.

Provides test database, test client, and authentication helpers.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import Base, get_db_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User, UserRole

settings = get_settings()

# Use a test database
TEST_DATABASE_URL = settings.database_url.replace(
    settings.postgres_db, f"{settings.postgres_db}_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide a test HTTP client with database override."""

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        email="test-admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("testpassword"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_agent(db_session: AsyncSession) -> User:
    """Create a test support agent."""
    user = User(
        email="test-agent@test.com",
        full_name="Test Agent",
        hashed_password=hash_password("testpassword"),
        role=UserRole.SUPPORT_AGENT,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_customer(db_session: AsyncSession) -> User:
    """Create a test customer."""
    user = User(
        email="test-customer@test.com",
        full_name="Test Customer",
        hashed_password=hash_password("testpassword"),
        role=UserRole.CUSTOMER,
        customer_tier="enterprise",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    """Generate Authorization header for a user."""
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}
