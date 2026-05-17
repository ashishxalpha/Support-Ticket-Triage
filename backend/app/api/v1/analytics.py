"""
Analytics API endpoints for the dashboard.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.deps import DBSession, require_agent_or_above
from app.models.user import User
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_overview(
    db: DBSession,
    _: User = Depends(require_agent_or_above),
) -> dict[str, Any]:
    """Get high-level dashboard overview metrics."""
    service = AnalyticsService(db)
    return await service.get_overview()


@router.get("/tickets")
async def get_ticket_analytics(
    db: DBSession,
    _: User = Depends(require_agent_or_above),
) -> dict[str, Any]:
    """Get detailed ticket analytics (by category, priority, status, daily trends)."""
    service = AnalyticsService(db)
    return await service.get_ticket_analytics()


@router.get("/sla")
async def get_sla_metrics(
    db: DBSession,
    _: User = Depends(require_agent_or_above),
) -> dict[str, Any]:
    """Get SLA metrics (response time, resolution time)."""
    service = AnalyticsService(db)
    return await service.get_sla_metrics()


@router.get("/agents")
async def get_agent_workload(
    db: DBSession,
    _: User = Depends(require_agent_or_above),
) -> list[dict[str, Any]]:
    """Get agent workload distribution."""
    service = AnalyticsService(db)
    return await service.get_agent_workload()


@router.get("/ai-performance")
async def get_ai_performance(
    db: DBSession,
    _: User = Depends(require_agent_or_above),
) -> dict[str, Any]:
    """Get AI triage accuracy metrics."""
    service = AnalyticsService(db)
    return await service.get_ai_performance()
