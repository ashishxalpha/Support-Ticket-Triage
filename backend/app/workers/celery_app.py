"""
Celery application configuration.

Configures the Celery worker with Redis broker, retry policies,
task routing, and serialization settings.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "support_triage",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    # Retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result
    result_expires=3600,  # 1 hour
    # Worker
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    worker_concurrency=4,
    # Task routing
    task_routes={
        "app.workers.tasks.triage.*": {"queue": "triage"},
        "app.workers.tasks.notifications.*": {"queue": "notifications"},
    },
    task_default_queue="default",
    # Dead letter handling
    task_annotations={
        "app.workers.tasks.triage.process_ticket_triage": {
            "max_retries": 3,
            "default_retry_delay": 30,
        },
    },
)

celery_app.autodiscover_tasks([
    "app.workers.tasks",
])
