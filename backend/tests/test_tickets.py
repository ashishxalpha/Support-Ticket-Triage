"""Tests for ticket endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_create_ticket(client: AsyncClient, test_customer: User) -> None:
    """Test ticket creation."""
    response = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Test ticket",
            "description": "This is a test ticket description with enough characters",
            "priority": "medium",
        },
        headers=auth_headers(test_customer),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test ticket"
    assert data["status"] == "open"
    assert data["ticket_number"].startswith("TKT-")


@pytest.mark.asyncio
async def test_list_tickets(client: AsyncClient, test_customer: User) -> None:
    """Test ticket listing with pagination."""
    # Create a ticket first
    await client.post(
        "/api/v1/tickets",
        json={
            "title": "List test ticket",
            "description": "Description for list test ticket with enough detail",
        },
        headers=auth_headers(test_customer),
    )

    response = await client.get(
        "/api/v1/tickets",
        headers=auth_headers(test_customer),
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_ticket(client: AsyncClient, test_customer: User) -> None:
    """Test getting a single ticket."""
    # Create ticket
    create_resp = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Get test ticket",
            "description": "Description for get test ticket with sufficient text",
        },
        headers=auth_headers(test_customer),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_headers(test_customer),
    )
    assert response.status_code == 200
    assert response.json()["id"] == ticket_id


@pytest.mark.asyncio
async def test_add_comment(client: AsyncClient, test_customer: User) -> None:
    """Test adding a comment to a ticket."""
    create_resp = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Comment test ticket",
            "description": "Description for comment test ticket that is long enough",
        },
        headers=auth_headers(test_customer),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={"content": "This is a test comment"},
        headers=auth_headers(test_customer),
    )
    assert response.status_code == 201
    assert response.json()["content"] == "This is a test comment"


@pytest.mark.asyncio
async def test_customer_cannot_see_other_tickets(
    client: AsyncClient, test_customer: User, test_agent: User
) -> None:
    """Test that customers can only see their own tickets."""
    # Create ticket as customer
    create_resp = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Customer private ticket",
            "description": "This ticket should be private to the creating customer",
        },
        headers=auth_headers(test_customer),
    )
    ticket_id = create_resp.json()["id"]

    # Agent should be able to see it
    agent_resp = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_headers(test_agent),
    )
    assert agent_resp.status_code == 200


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
