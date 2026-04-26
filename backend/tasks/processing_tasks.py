"""Celery tasks for document processing pipeline."""

import io
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import settings
from backend.core.storage import get_storage_client
from backend.core.types import JobStatus
from backend.models.db_models import DocumentJob, PIIEntity, RedactionReport
from backend.services.document_processor import DocumentProcessor
from backend.services.pii_detector import PIIDetector
from backend.services.redaction_engine import RedactionEngine
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _text_to_pdf(text: str, original_filename: str) -> bytes:
    """Convert redacted text to a PDF document."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Heading2"],
        fontSize=13,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
    )
    redacted_style = ParagraphStyle(
        "redacted",
        parent=body_style,
        textColor=(0.8, 0, 0),
        fontName="Helvetica-Bold",
    )

    story = []
    story.append(Paragraph(f"Redacted: {original_filename}", title_style))
    story.append(Spacer(1, 4 * mm))

    for line in text.splitlines():
        if not line.strip():
            story.append(Spacer(1, 3 * mm))
            continue
        # Escape HTML special chars for ReportLab
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if "[REDACTED]" in safe or "****" in safe:
            story.append(Paragraph(safe, redacted_style))
        else:
            story.append(Paragraph(safe, body_style))

    doc.build(story)
    return buf.getvalue()

_sync_engine = None
_SyncSession = None


def _get_session() -> Session:
    """Get a synchronous SQLAlchemy session."""
    global _sync_engine, _SyncSession
    if _sync_engine is None:
        sync_url = settings.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )
        _sync_engine = create_engine(sync_url, pool_pre_ping=True)
        _SyncSession = sessionmaker(bind=_sync_engine)
    return _SyncSession()


def _mark_job_failed(job_id: str, error: str) -> None:
    """Mark a job as FAILED in the database."""
    try:
        with _get_session() as session:
            job = session.execute(
                select(DocumentJob).where(DocumentJob.id == UUID(job_id))
            ).scalar_one_or_none()
            if job:
                job.status = JobStatus.FAILED.value
                job.updated_at = datetime.utcnow()
                if not job.details:
                    job.details = {}
                job.details = {**job.details, "error": error}
                session.commit()
    except Exception as mark_error:
        logger.error(f"Failed to mark job {job_id} as failed: {mark_error}")


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=1800,  # Hard timeout: 30 minutes
    soft_time_limit=1700,  # Soft timeout: 28 minutes (allows graceful shutdown)
)
def extract_text_task(self, job_id: str):
    """Extract text from uploaded document."""
    try:
        logger.info(f"Starting text extraction for job {job_id}")

        with _get_session() as session:
            job = session.execute(
                select(DocumentJob).where(DocumentJob.id == UUID(job_id))
            ).scalar_one_or_none()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            job.status = JobStatus.EXTRACTING.value
            job.updated_at = datetime.utcnow()
            session.commit()

            storage = get_storage_client()
            file_bytes = storage.download_file(job.storage_key)

            processor = DocumentProcessor()
            extracted = processor.extract_text(file_bytes, job.filename)

            if not job.details:
                job.details = {}
            job.details = {
                **job.details,
                "extracted_text": extracted.text,
                "scan_type": extracted.scan_type.value,
                "page_count": extracted.page_count,
                "char_count": extracted.char_count,
            }

            job.status = JobStatus.PII_DETECTING.value
            job.updated_at = datetime.utcnow()
            session.commit()

            logger.info(
                f"Text extraction completed for job {job_id}: "
                f"{extracted.char_count} chars, {extracted.page_count} pages"
            )
            char_count = extracted.char_count

        detect_pii_task.apply_async(args=[job_id], countdown=1)
        return {"job_id": job_id, "char_count": char_count}

    except Exception as e:
        logger.error(f"Text extraction failed for job {job_id}: {e}")
        _mark_job_failed(job_id, str(e))
        raise


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    time_limit=900,  # Hard timeout: 15 minutes
    soft_time_limit=840,  # Soft timeout: 14 minutes
)
def detect_pii_task(self, job_id: str):
    """Detect PII entities in extracted text."""
    try:
        logger.info(f"Starting PII detection for job {job_id}")

        with _get_session() as session:
            job = session.execute(
                select(DocumentJob).where(DocumentJob.id == UUID(job_id))
            ).scalar_one_or_none()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            extracted_text = (job.details or {}).get("extracted_text", "")
            if not extracted_text:
                raise ValueError(f"No extracted text found for job {job_id}")

            detector = PIIDetector()
            detection_result = detector.detect(extracted_text)

            for entity in detection_result.entities:
                pii_entity = PIIEntity(
                    job_id=job.id,
                    entity_type=entity.entity_type,
                    start_offset=entity.start_offset,
                    end_offset=entity.end_offset,
                    confidence=entity.confidence,
                    subtype=entity.subtype,
                )
                session.add(pii_entity)

            job.risk_score = detection_result.risk_score
            job.risk_band = detection_result.risk_band.value
            job.status = JobStatus.PII_DETECTED.value
            job.updated_at = datetime.utcnow()

            if not job.details:
                job.details = {}
            job.details = {
                **job.details,
                "entity_counts": detection_result.entity_counts,
                "total_entities": len(detection_result.entities),
                "risk_explanation": detection_result.risk_explanation,
            }

            session.commit()

            logger.info(
                f"PII detection completed for job {job_id}: "
                f"{len(detection_result.entities)} entities, "
                f"risk_score={detection_result.risk_score:.2f}"
            )
            result = {
                "entity_count": len(detection_result.entities),
                "risk_score": detection_result.risk_score,
                "risk_band": detection_result.risk_band.value,
            }

        from backend.tasks.om_tasks import ingest_to_openmetadata_task
        ingest_to_openmetadata_task.apply_async(args=[job_id], countdown=2)

        return result

    except Exception as e:
        logger.error(f"PII detection failed for job {job_id}: {e}")
        _mark_job_failed(job_id, str(e))
        raise


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    time_limit=1200,  # Hard timeout: 20 minutes
    soft_time_limit=1140,  # Soft timeout: 19 minutes
)
def redact_document_task(self, job_id: str, redaction_level: str):
    """Redact PII from document."""
    try:
        logger.info(f"Starting redaction for job {job_id} with level {redaction_level}")

        from backend.core.types import RedactionLevel

        with _get_session() as session:
            job = session.execute(
                select(DocumentJob).where(DocumentJob.id == UUID(job_id))
            ).scalar_one_or_none()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            job.status = JobStatus.REDACTING.value
            job.updated_at = datetime.utcnow()
            session.commit()

            extracted_text = (job.details or {}).get("extracted_text", "")
            if not extracted_text:
                raise ValueError(f"No extracted text found for job {job_id}")

            pii_entities = session.execute(
                select(PIIEntity).where(PIIEntity.job_id == job.id)
            ).scalars().all()

            from backend.services.pii_detector import PIIEntity as PIIEntityDC
            entities = [
                PIIEntityDC(
                    entity_type=e.entity_type,
                    start_offset=e.start_offset,
                    end_offset=e.end_offset,
                    confidence=e.confidence,
                    subtype=e.subtype,
                )
                for e in pii_entities
            ]

            engine = RedactionEngine()
            level = RedactionLevel(redaction_level)
            redaction_result = engine.redact(extracted_text, entities, level)

            storage = get_storage_client()
            redacted_key = f"{job.storage_key}.redacted.pdf"
            pdf_bytes = _text_to_pdf(redaction_result.redacted_text, job.filename)
            storage.upload_file(
                redacted_key,
                pdf_bytes,
                "application/pdf",
            )

            report_json = engine.generate_report(
                job_id=job.id,
                filename=job.filename,
                redaction_level=level,
                result=redaction_result,
                entities=entities,
                risk_score_before=job.risk_score or 0.0,
                risk_score_after=0.0,
            )

            redaction_report = RedactionReport(
                job_id=job.id,
                redaction_level=level.value,
                redacted_storage_key=redacted_key,
                report_json=report_json,
                total_entities_redacted=redaction_result.entities_redacted,
                risk_score_before=job.risk_score or 0.0,
                risk_score_after=0.0,
            )
            session.add(redaction_report)

            job.status = JobStatus.COMPLETED.value
            job.updated_at = datetime.utcnow()
            job.redacted_storage_key = redacted_key

            if not job.details:
                job.details = {}
            job.details = {
                **job.details,
                "redacted_storage_key": redacted_key,
                "entities_redacted": redaction_result.entities_redacted,
            }

            session.commit()

            logger.info(
                f"Redaction completed for job {job_id}: "
                f"{redaction_result.entities_redacted} entities redacted"
            )
            result = {
                "entities_redacted": redaction_result.entities_redacted,
                "redacted_key": redacted_key,
            }

        from backend.tasks.om_tasks import ingest_redacted_to_om_task
        ingest_redacted_to_om_task.apply_async(args=[job_id, redaction_level], countdown=2)

        return result

    except Exception as e:
        logger.error(f"Redaction failed for job {job_id}: {e}")
        _mark_job_failed(job_id, str(e))
        raise
