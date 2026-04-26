"""Celery application configuration for async task processing."""

import logging

from celery import Celery
from kombu import Exchange, Queue

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "morolo",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_acks_late=True,  # Acknowledge after task completes (not when started)
    task_reject_on_worker_lost=True,  # Re-queue if worker crashes
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to Redis
    # Worker
    worker_prefetch_multiplier=1,  # Fetch one task at a time (fair distribution)
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (memory leak prevention)
    # Logging
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s",
)

# Dead Letter Queue (DLQ) configuration
# Failed tasks after max retries are routed to morolo.dlq
default_exchange = Exchange("morolo", type="direct")
dlq_exchange = Exchange("morolo.dlq", type="direct")

celery_app.conf.task_queues = (
    # Default queue
    Queue(
        "morolo.default",
        exchange=default_exchange,
        routing_key="morolo.default",
    ),
    # Dead letter queue
    Queue(
        "morolo.dlq",
        exchange=dlq_exchange,
        routing_key="morolo.dlq",
    ),
)

# Default routing
celery_app.conf.task_default_queue = "morolo.default"
celery_app.conf.task_default_exchange = "morolo"
celery_app.conf.task_default_routing_key = "morolo.default"

# Task routes
celery_app.conf.task_routes = {
    "backend.tasks.processing_tasks.*": {"queue": "morolo.default"},
    "backend.tasks.om_tasks.*": {"queue": "morolo.default"},
}

# Auto-discover tasks
celery_app.autodiscover_tasks(
    [
        "backend.tasks.processing_tasks",
        "backend.tasks.om_tasks",
        "backend.tasks.audit",
    ]
)

logger.info("Celery app configured with DLQ support")
