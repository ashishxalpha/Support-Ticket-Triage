"""Tests for authentication endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    """Test successful user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@test.com",
            "password": "securepassword123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "customer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_customer: User) -> None:
    """Test registration with existing email fails."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_customer.email,
            "password": "securepassword123",
            "full_name": "Duplicate User",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_customer: User) -> None:
    """Test successful login returns tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_customer.email, "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_customer: User) -> None:
    """Test login with wrong password fails."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_customer.email, "password": "wrongpassword"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_admin: User) -> None:
    """Test getting the current user profile."""
    response = await client.get(
        "/api/v1/auth/me",
        headers=auth_headers(test_admin),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_admin.email
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_unauthorized_without_token(client: AsyncClient) -> None:
    """Test that endpoints require authentication."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
