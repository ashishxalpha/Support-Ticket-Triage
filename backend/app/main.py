"""
FastAPI application entrypoint.

Assembles all routers, middleware, exception handlers, and lifecycle events.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.redis import close_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    setup_logging()
    await init_db()
    yield
    await close_db()
    await close_redis()


app = FastAPI(
    title="AI Support Ticket Triage System",
    description=(
        "Production-grade AI-powered support ticket management and triage platform. "
        "Classifies tickets, predicts priority, routes to teams, generates responses, "
        "and provides semantic search via vector embeddings."
    ),
    version=settings.app_version,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware (Starlette: last added = first to execute) ─────
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.rate_limiting import RateLimitMiddleware

# Inner middleware (added first, runs after CORS)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# CORS must be outermost (added last, runs first) to handle preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# ── Exception Handlers ──────────────────────────────────────
register_exception_handlers(app)

# ── Routers ─────────────────────────────────────────────────
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.teams import router as teams_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.health import router as health_router
from app.api.v1.websocket import router as ws_router
from app.api.v1.knowledge_base import router as kb_router
from app.api.v1.webhooks import router as webhooks_router

API_V1_PREFIX = "/api/v1"

app.include_router(health_router)
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(users_router, prefix=API_V1_PREFIX)
app.include_router(tickets_router, prefix=API_V1_PREFIX)
app.include_router(teams_router, prefix=API_V1_PREFIX)
app.include_router(analytics_router, prefix=API_V1_PREFIX)
app.include_router(ws_router, prefix=API_V1_PREFIX)
app.include_router(kb_router, prefix=API_V1_PREFIX)
app.include_router(webhooks_router, prefix=API_V1_PREFIX)

# ── Prometheus Monitoring ───────────────────────────────────
Instrumentator().instrument(app).expose(app)
