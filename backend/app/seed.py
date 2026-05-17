"""
Seed data — creates realistic sample data for development and demos.

Run with: python -m app.seed
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.core.database import async_session_factory, engine, init_db
from app.core.security import hash_password
from app.models.notification import Notification
from app.models.team import Team, TeamMember
from app.models.ticket import (
    Ticket,
    TicketActivity,
    TicketCategory,
    TicketComment,
    TicketPriority,
    TicketStatus,
)
from app.models.user import User, UserRole

settings = get_settings()

SAMPLE_TICKETS = [
    {
        "title": "Cannot process payment with credit card",
        "description": "I've been trying to upgrade my plan to Enterprise but my credit card keeps getting declined. I've verified the card details are correct and the card works on other sites. Error message says 'Payment processing failed - Error Code: PY-4001'. This is urgent as our team needs the additional seats by end of week.",
        "category": TicketCategory.BILLING,
        "priority": TicketPriority.HIGH,
    },
    {
        "title": "API rate limiting is too aggressive",
        "description": "Our integration is hitting rate limits even though we're well within our plan's API quota. We're on the Business plan with 10,000 requests/hour but getting 429 errors after only ~2,000 requests. This is affecting our production pipeline and causing data sync failures. Can you check our account's rate limit configuration?",
        "category": TicketCategory.TECHNICAL,
        "priority": TicketPriority.HIGH,
    },
    {
        "title": "Dashboard charts not loading after latest update",
        "description": "Since the update yesterday, none of the analytics charts on the dashboard are rendering. I see a blank white space where the charts should be. Console shows JavaScript errors related to 'recharts'. This affects all users in our organization. Browser: Chrome 120, OS: macOS Sonoma.",
        "category": TicketCategory.BUG,
        "priority": TicketPriority.HIGH,
    },
    {
        "title": "Request: Add Slack integration for notifications",
        "description": "We'd love to have native Slack integration for ticket notifications. Currently we're using a custom webhook but it's unreliable. Ideally we'd want: 1) New ticket alerts in a channel, 2) Assignment notifications as DMs, 3) Status change updates. This would significantly improve our team's response time.",
        "category": TicketCategory.FEATURE_REQUEST,
        "priority": TicketPriority.LOW,
    },
    {
        "title": "Suspicious login attempts on our account",
        "description": "We've noticed multiple failed login attempts from IP addresses in countries where we don't have employees. The audit log shows 47 failed attempts in the last 24 hours from IPs in Russia and China. Our admin account email is admin@acmecorp.com. Please investigate immediately and help us secure our account.",
        "category": TicketCategory.SECURITY,
        "priority": TicketPriority.CRITICAL,
    },
    {
        "title": "Need to add 5 new team members to our account",
        "description": "We just hired 5 new support agents and need to add them to our organization account. Their emails are: john.d@acme.com, sarah.k@acme.com, mike.r@acme.com, lisa.t@acme.com, david.w@acme.com. They should all have Agent role permissions. We're on the Business plan.",
        "category": TicketCategory.ACCOUNT,
        "priority": TicketPriority.MEDIUM,
    },
    {
        "title": "Request refund for double charge on January invoice",
        "description": "We were charged twice for our January subscription - $499 on Jan 1st and another $499 on Jan 3rd. Our account ID is ACC-78234. Please refund the duplicate charge of $499. I've attached screenshots of both charges from our bank statement.",
        "category": TicketCategory.REFUND,
        "priority": TicketPriority.MEDIUM,
    },
    {
        "title": "How to set up SSO with Okta?",
        "description": "We're looking to implement SSO using Okta for our organization. I've read through the documentation but I'm not sure about the SAML configuration steps. Could you provide a step-by-step guide or schedule a call to walk us through the setup? We have about 200 users that need to be migrated.",
        "category": TicketCategory.GENERAL_INQUIRY,
        "priority": TicketPriority.LOW,
    },
    {
        "title": "Data export failing for reports over 10,000 rows",
        "description": "When trying to export CSV reports with more than 10,000 rows, the export job hangs and eventually times out after 5 minutes. Smaller exports work fine. We need to export our full ticket history (approximately 50,000 records) for an audit. This has been happening for the past week.",
        "category": TicketCategory.BUG,
        "priority": TicketPriority.MEDIUM,
    },
    {
        "title": "URGENT: Production API returning 500 errors",
        "description": "Our production environment is experiencing intermittent 500 errors from the /api/v1/tickets endpoint. Started approximately 30 minutes ago. Affecting roughly 40% of requests. Our entire customer-facing support portal is down. This is a P0 incident for us. Error response body: {'error': 'internal_server_error', 'trace_id': 'abc123def456'}. NEED IMMEDIATE ASSISTANCE.",
        "category": TicketCategory.TECHNICAL,
        "priority": TicketPriority.CRITICAL,
    },
    {
        "title": "Webhook deliveries failing silently",
        "description": "We configured webhooks to POST to https://api.oursite.com/webhooks/support but we're not receiving any events. The webhook dashboard shows all deliveries as 'pending' with no response code. We've verified our endpoint is accessible from the public internet and returns 200. Webhook was configured 3 days ago.",
        "category": TicketCategory.TECHNICAL,
        "priority": TicketPriority.HIGH,
    },
    {
        "title": "Cancel subscription and process final refund",
        "description": "We've decided to move to a different platform. Please cancel our subscription effective immediately and process a prorated refund for the remaining days in our billing cycle. Account: ACC-92341, Plan: Enterprise Annual, Last payment: $5,988 on Dec 1st.",
        "category": TicketCategory.REFUND,
        "priority": TicketPriority.MEDIUM,
    },
    {
        "title": "Feature request: Custom fields for tickets",
        "description": "We need the ability to add custom fields to tickets. Our use case requires tracking: 1) Product version affected, 2) Customer environment (cloud/on-prem), 3) SLA tier, 4) Business unit. This would help us route and prioritize tickets more effectively. Happy to discuss requirements in detail.",
        "category": TicketCategory.FEATURE_REQUEST,
        "priority": TicketPriority.LOW,
    },
    {
        "title": "Two-factor authentication not sending SMS codes",
        "description": "I enabled 2FA on my account last week with SMS verification. Today when trying to log in, the SMS code never arrives. I've waited 10+ minutes and tried resending 5 times. My phone number is correct and I can receive other SMS messages. I'm locked out of my account and have a critical deadline today.",
        "category": TicketCategory.SECURITY,
        "priority": TicketPriority.HIGH,
    },
    {
        "title": "Billing discrepancy - charged for inactive users",
        "description": "We're being charged for 45 user seats but only have 32 active users. The 13 inactive users were deactivated 2 months ago but are still showing up on our invoice. Please adjust our billing to reflect only active users and credit us for the overcharges from the past 2 months.",
        "category": TicketCategory.BILLING,
        "priority": TicketPriority.MEDIUM,
    },
]


async def seed_database() -> None:
    """Populate the database with realistic sample data."""
    await init_db()

    async with async_session_factory() as session:
        # Check if already seeded
        from sqlalchemy import select, func
        count = await session.execute(select(func.count(User.id)))
        if (count.scalar() or 0) > 0:
            print("Database already seeded. Skipping.")
            return

        print("🌱 Seeding database...")

        # ── Create Users ─────────────────────────────────────
        admin = User(
            email="admin@support-triage.ai",
            full_name="System Admin",
            hashed_password=hash_password("admin123!"),
            role=UserRole.ADMIN,
            department="Engineering",
        )

        manager = User(
            email="manager@support-triage.ai",
            full_name="Sarah Mitchell",
            hashed_password=hash_password("manager123!"),
            role=UserRole.SUPPORT_MANAGER,
            department="Support Operations",
        )

        agents = []
        agent_data = [
            ("alex.johnson@support-triage.ai", "Alex Johnson"),
            ("maria.garcia@support-triage.ai", "Maria Garcia"),
            ("james.wilson@support-triage.ai", "James Wilson"),
            ("emily.chen@support-triage.ai", "Emily Chen"),
            ("raj.patel@support-triage.ai", "Raj Patel"),
            ("anna.kowalski@support-triage.ai", "Anna Kowalski"),
            ("tom.nakamura@support-triage.ai", "Tom Nakamura"),
            ("lisa.brown@support-triage.ai", "Lisa Brown"),
        ]
        for email, name in agent_data:
            agent = User(
                email=email,
                full_name=name,
                hashed_password=hash_password("agent123!"),
                role=UserRole.SUPPORT_AGENT,
                department="Customer Support",
            )
            agents.append(agent)

        customers = []
        customer_data = [
            ("customer1@acmecorp.com", "Bob Smith", "enterprise"),
            ("customer2@techstart.io", "Alice Wong", "business"),
            ("customer3@globex.com", "Carlos Rodriguez", "standard"),
            ("customer4@initech.com", "Diana Prince", "enterprise"),
            ("customer5@umbrella.co", "Ethan Hunt", "standard"),
        ]
        for email, name, tier in customer_data:
            customer = User(
                email=email,
                full_name=name,
                hashed_password=hash_password("customer123!"),
                role=UserRole.CUSTOMER,
                customer_tier=tier,
            )
            customers.append(customer)

        session.add_all([admin, manager, *agents, *customers])
        await session.flush()

        print(f"  ✓ Created {2 + len(agents) + len(customers)} users")

        # ── Create Teams ─────────────────────────────────────
        teams_data = [
            ("Billing Team", "billing", "Handles payment, invoicing, and subscription issues", "#f59e0b"),
            ("Platform Team", "platform", "Handles technical issues, bugs, and feature requests", "#3b82f6"),
            ("DevOps Team", "devops", "Handles infrastructure, deployment, and performance issues", "#8b5cf6"),
            ("Security Team", "security", "Handles security incidents, vulnerabilities, and access control", "#ef4444"),
            ("Customer Success", "customer-success", "Handles account management, onboarding, and general inquiries", "#10b981"),
        ]

        teams = []
        for name, slug, desc, color in teams_data:
            team = Team(name=name, slug=slug, description=desc, color=color)
            teams.append(team)

        session.add_all(teams)
        await session.flush()

        # Assign agents to teams
        team_assignments = [
            (0, [0, 1]),     # Billing: Alex, Maria
            (1, [2, 3, 4]),  # Platform: James, Emily, Raj
            (2, [4, 5]),     # DevOps: Raj, Anna
            (3, [5, 6]),     # Security: Anna, Tom
            (4, [1, 7]),     # Customer Success: Maria, Lisa
        ]
        for team_idx, agent_indices in team_assignments:
            for i, agent_idx in enumerate(agent_indices):
                member = TeamMember(
                    team_id=teams[team_idx].id,
                    user_id=agents[agent_idx].id,
                    role="lead" if i == 0 else "member",
                )
                session.add(member)

        await session.flush()
        print(f"  ✓ Created {len(teams)} teams with member assignments")

        # ── Create Tickets ───────────────────────────────────
        statuses = list(TicketStatus)
        now = datetime.now(timezone.utc)

        for i, ticket_data in enumerate(SAMPLE_TICKETS):
            status = random.choice(statuses[:4])  # Mostly open/in_progress
            created_at = now - timedelta(days=random.randint(1, 30), hours=random.randint(0, 23))

            ticket = Ticket(
                ticket_number=f"TKT-{i+1:05d}",
                title=ticket_data["title"],
                description=ticket_data["description"],
                category=ticket_data["category"],
                priority=ticket_data["priority"],
                status=status,
                customer_id=random.choice(customers).id,
                assigned_agent_id=random.choice(agents).id if status != TicketStatus.OPEN else None,
                tags=random.sample(["urgent", "enterprise", "api", "billing", "security", "bug", "feature"], k=random.randint(1, 3)),
                source=random.choice(["web", "email", "api", "slack"]),
                created_at=created_at,
                is_triaged=random.choice([True, False]),
            )

            # Add AI data for triaged tickets
            if ticket.is_triaged:
                ticket.predicted_category = ticket_data["category"]
                ticket.predicted_priority = ticket_data["priority"]
                ticket.category_confidence = round(random.uniform(0.75, 0.98), 2)
                ticket.priority_confidence = round(random.uniform(0.70, 0.95), 2)
                ticket.ai_summary = f"Customer reports {ticket_data['title'].lower()}. Requires attention from the appropriate team."
                ticket.sentiment_score = round(random.uniform(-0.8, 0.2), 2)
                ticket.sentiment_label = random.choice(["negative", "neutral", "very_negative"])
                ticket.ai_confidence = round(random.uniform(0.7, 0.95), 2)

            if status in (TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED):
                ticket.first_response_at = created_at + timedelta(hours=random.randint(1, 8))
            if status == TicketStatus.RESOLVED:
                ticket.resolved_at = created_at + timedelta(hours=random.randint(4, 72))

            session.add(ticket)
            await session.flush()

            # Add a comment to some tickets
            if random.random() > 0.4:
                comment = TicketComment(
                    ticket_id=ticket.id,
                    user_id=random.choice(agents).id,
                    content="Thank you for reaching out. I'm looking into this issue and will update you shortly.",
                    is_internal=False,
                )
                session.add(comment)

            # Add activity log
            activity = TicketActivity(
                ticket_id=ticket.id,
                user_id=ticket.customer_id,
                action="ticket_created",
                created_at=created_at,
            )
            session.add(activity)

        await session.flush()
        print(f"  ✓ Created {len(SAMPLE_TICKETS)} sample tickets")

        await session.commit()
        print("✅ Database seeded successfully!")
        print()
        print("  Login credentials:")
        print("  ──────────────────")
        print("  Admin:    admin@support-triage.ai / admin123!")
        print("  Manager:  manager@support-triage.ai / manager123!")
        print("  Agent:    alex.johnson@support-triage.ai / agent123!")
        print("  Customer: customer1@acmecorp.com / customer123!")


if __name__ == "__main__":
    asyncio.run(seed_database())
