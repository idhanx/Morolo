"""Audit logging utilities for task execution."""

import logging
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings
from backend.core.types import AuditAction
from backend.models.db_models import AuditLog

logger = logging.getLogger(__name__)


def _get_session_maker():
    """Create a fresh async engine+session bound to the current event loop."""
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def log_action(
    job_id: UUID,
    action: AuditAction,
    actor: str,
    details: Dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    try:
        async with _get_session_maker()() as session:
            audit_log = AuditLog(
                job_id=job_id,
                action=action.value if isinstance(action, AuditAction) else action,
                actor=actor,
                details=details or {},
                ip_address=ip_address,
                timestamp=datetime.utcnow(),
            )
            session.add(audit_log)
            await session.commit()
            logger.debug(f"Audit log created: job_id={job_id}, action={action}, actor={actor}")
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


async def log_task_start(
    job_id: UUID,
    task_name: str,
    details: Dict[str, Any] | None = None,
) -> None:
    await log_action(
        job_id=job_id,
        action=AuditAction.PROCESS,
        actor="system",
        details={"event": "task_start", "task_name": task_name, **(details or {})},
    )


async def log_task_complete(
    job_id: UUID,
    task_name: str,
    details: Dict[str, Any] | None = None,
) -> None:
    await log_action(
        job_id=job_id,
        action=AuditAction.PROCESS,
        actor="system",
        details={"event": "task_complete", "task_name": task_name, **(details or {})},
    )


async def log_task_failure(
    job_id: UUID,
    task_name: str,
    error: str,
    details: Dict[str, Any] | None = None,
) -> None:
    await log_action(
        job_id=job_id,
        action=AuditAction.PROCESS,
        actor="system",
        details={"event": "task_failure", "task_name": task_name, "error": error, **(details or {})},
    )