"""Celery tasks for OpenMetadata integration."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from pybreaker import CircuitBreakerError
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import settings
from backend.core.types import AuditAction
from backend.models.db_models import AuditLog, DocumentJob, PIIEntity
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_om_service = None
_sync_engine = None
_SyncSession = None


def get_om_service():
    global _om_service
    if _om_service is None:
        from backend.services.om_integration import OMIntegrationService
        _om_service = OMIntegrationService()
    return _om_service


def get_sync_session() -> Session:
    """Get a synchronous SQLAlchemy session for use in Celery workers."""
    global _sync_engine, _SyncSession
    if _sync_engine is None:
        # Convert asyncpg URL to psycopg2
        sync_url = settings.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )
        _sync_engine = create_engine(sync_url, pool_pre_ping=True)
        _SyncSession = sessionmaker(bind=_sync_engine)
    return _SyncSession()


@celery_app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(CircuitBreakerError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=600,  # Hard timeout: 10 minutes
    soft_time_limit=540,  # Soft timeout: 9 minutes
)
def ingest_to_openmetadata_task(self, job_id: str):
    """Ingest original document to OpenMetadata."""
    logger.info("Starting OM ingestion for job %s", job_id)
    om_service = get_om_service()

    try:
        # Fetch job data synchronously
        with get_sync_session() as session:
            job = session.execute(
                select(DocumentJob).where(DocumentJob.id == UUID(job_id))
            ).scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            pii_entities = session.execute(
                select(PIIEntity).where(PIIEntity.job_id == job.id)
            ).scalars().all()

            pii_types = list(set(e.entity_type for e in pii_entities))
            job_id_str = str(job.id)
            filename = job.filename
            file_size = job.file_size
            storage_key = job.storage_key
            risk_score = job.risk_score or 0.0
            risk_band = job.risk_band or "LOW"

        # Call OM synchronously
        om_service.ensure_classification_hierarchy()
        entity_fqn = om_service.create_container_entity(
            job_id_str, filename, file_size, storage_key,
            risk_score, risk_band, pii_types, False,
        )
        om_service.apply_tags(entity_fqn, pii_types)
        om_service.register_pipeline_run(job_id_str, "success")

        # Save FQN back to DB
        with get_sync_session() as session:
            job = session.execute(
                select(DocumentJob).where(DocumentJob.id == UUID(job_id))
            ).scalar_one_or_none()

            if job:
                job.om_entity_fqn = entity_fqn
                if not job.details:
                    job.details = {}
                job.details = {**job.details, "om_entity_fqn": entity_fqn}

                if job.risk_score and job.risk_score >= 51:
                    policy_status = om_service.verify_policy_enforcement(entity_fqn)
                    audit_log = AuditLog(
                        job_id=job.id,
                        action=AuditAction.APPLY_POLICY.value,
                        actor="system",
                        details={
                            "entity_fqn": entity_fqn,
                            "policy_will_apply": policy_status["policy_will_apply"],
                            "matching_tags": policy_status["matching_tags"],
                            "risk_score": job.risk_score,
                        },
                    )
                    session.add(audit_log)

                session.commit()

        logger.info("OM ingestion completed for job %s: %s", job_id, entity_fqn)
        return {"entity_fqn": entity_fqn, "pii_types": pii_types}

    except CircuitBreakerError as e:
        logger.warning("OM circuit breaker open for job %s: %s", job_id, e)
        raise
    except Exception as e:
        logger.error("OM ingestion failed for job %s: %s", job_id, e)
        return {"error": str(e), "entity_fqn": None}


@celery_app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(CircuitBreakerError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def ingest_redacted_to_om_task(self, job_id: str, redaction_level: str):
    """Ingest redacted document to OpenMetadata and create lineage."""
    logger.info("Starting OM ingestion for redacted job %s", job_id)
    om_service = get_om_service()

    try:
        # Fetch job data synchronously
        with get_sync_session() as session:
            job = session.execute(
                select(DocumentJob).where(DocumentJob.id == UUID(job_id))
            ).scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            redacted_key = job.redacted_storage_key or (job.details or {}).get("redacted_storage_key")
            if not redacted_key:
                raise ValueError(f"No redacted storage key for job {job_id}")

            pii_entities = session.execute(
                select(PIIEntity).where(PIIEntity.job_id == job.id)
            ).scalars().all()

            pii_types = list(set(e.entity_type for e in pii_entities))
            job_id_str = str(job.id)
            filename = job.filename
            original_fqn = job.om_entity_fqn or (job.details or {}).get("om_entity_fqn")

        # OM calls synchronously
        redacted_fqn = om_service.create_container_entity(
            job_id_str, filename, 0,
            redacted_key, 0.0, "LOW", pii_types, True,
        )
        om_service.apply_tags(redacted_fqn, pii_types)

        lineage_id = None
        if not original_fqn:
            logger.warning("No original FQN for job %s — skipping lineage", job_id)
        else:
            lineage_id = om_service.create_lineage_edge(
                original_fqn, redacted_fqn,
                redaction_level, datetime.now(timezone.utc),
            )
            if lineage_id:
                logger.info("Lineage created: %s → %s", original_fqn, redacted_fqn)
            else:
                logger.warning("Lineage failed: %s → %s", original_fqn, redacted_fqn)

        om_service.register_pipeline_run(job_id_str, "success")

        # Save back to DB
        with get_sync_session() as session:
            job = session.execute(
                select(DocumentJob).where(DocumentJob.id == UUID(job_id))
            ).scalar_one_or_none()

            if job:
                job.redacted_om_entity_fqn = redacted_fqn
                if not job.details:
                    job.details = {}
                job.details = {**job.details, "om_redacted_entity_fqn": redacted_fqn}
                session.commit()

        logger.info("OM ingestion completed for redacted job %s: %s", job_id, redacted_fqn)
        return {
            "redacted_fqn": redacted_fqn,
            "original_fqn": original_fqn,
            "lineage_created": lineage_id is not None,
        }

    except CircuitBreakerError as e:
        logger.warning("OM circuit breaker open for redacted job %s: %s", job_id, e)
        raise
    except Exception as e:
        logger.error("OM ingestion failed for redacted job %s: %s", job_id, e)
        return {"error": str(e), "redacted_fqn": None}