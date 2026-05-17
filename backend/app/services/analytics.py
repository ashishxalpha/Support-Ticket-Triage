"""
Analytics service — aggregates metrics for the dashboard.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole
from app.repositories.ticket import TicketRepository


class AnalyticsService:
    """Business logic for dashboard analytics and metrics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ticket_repo = TicketRepository(db)

    async def get_overview(self) -> dict[str, Any]:
        """Get high-level dashboard overview metrics."""
        status_counts = await self.ticket_repo.count_by_status()
        total_tickets = sum(status_counts.values())
        open_tickets = status_counts.get("open", 0) + status_counts.get("in_progress", 0)
        resolved_tickets = status_counts.get("resolved", 0) + status_counts.get("closed", 0)

        avg_resolution = await self.ticket_repo.avg_resolution_time_hours()
        avg_first_response = await self.ticket_repo.avg_first_response_time_hours()

        return {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolved_tickets": resolved_tickets,
            "avg_resolution_time_hours": avg_resolution,
            "avg_first_response_time_hours": avg_first_response,
            "tickets_by_status": status_counts,
        }

    async def get_ticket_analytics(self) -> dict[str, Any]:
        """Get detailed ticket analytics."""
        return {
            "by_category": await self.ticket_repo.count_by_category(),
            "by_priority": await self.ticket_repo.count_by_priority(),
            "by_status": await self.ticket_repo.count_by_status(),
            "daily_created": await self.ticket_repo.tickets_created_per_day(30),
        }

    async def get_sla_metrics(self) -> dict[str, Any]:
        """Get SLA-related metrics."""
        avg_resolution = await self.ticket_repo.avg_resolution_time_hours()
        avg_first_response = await self.ticket_repo.avg_first_response_time_hours()

        # SLA targets (configurable in production)
        sla_targets = {
            "first_response_hours": 4.0,
            "resolution_hours": 24.0,
        }

        return {
            "avg_resolution_time_hours": avg_resolution,
            "avg_first_response_time_hours": avg_first_response,
            "sla_targets": sla_targets,
            "first_response_met": (
                avg_first_response is not None
                and avg_first_response <= sla_targets["first_response_hours"]
            ),
            "resolution_met": (
                avg_resolution is not None
                and avg_resolution <= sla_targets["resolution_hours"]
            ),
        }

    async def get_agent_workload(self) -> list[dict[str, Any]]:
        """Get ticket counts per agent for workload distribution."""
        result = await self.db.execute(
            select(
                User.id,
                User.full_name,
                User.email,
                func.count(Ticket.id).label("active_tickets"),
            )
            .outerjoin(
                Ticket,
                (Ticket.assigned_agent_id == User.id)
                & (
                    Ticket.status.in_([
                        TicketStatus.OPEN,
                        TicketStatus.IN_PROGRESS,
                        TicketStatus.WAITING_ON_CUSTOMER,
                    ])
                ),
            )
            .where(User.role.in_([UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]))
            .where(User.is_active == True)  # noqa: E712
            .group_by(User.id, User.full_name, User.email)
            .order_by(func.count(Ticket.id).desc())
        )

        return [
            {
                "agent_id": str(row[0]),
                "name": row[1],
                "email": row[2],
                "active_tickets": row[3],
            }
            for row in result.all()
        ]

    async def get_ai_performance(self) -> dict[str, Any]:
        """Get AI triage accuracy metrics."""
        return await self.ticket_repo.ai_accuracy_stats()
