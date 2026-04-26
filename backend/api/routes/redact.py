"""Redaction endpoint for applying PII masking."""

import logging
import traceback
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_optional_user
from backend.api.middleware import limiter
from backend.api.schemas import RedactRequest
from backend.core.database import get_db
from backend.core.types import AuditAction, JobStatus
from backend.models.db_models import AuditLog, DocumentJob
from backend.tasks.processing_tasks import redact_document_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/redact", tags=["redaction"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger document redaction",
    description="Apply PII redaction to a document that has completed PII detection. "
    "Returns immediately. Use /status/{doc_id} to poll for completion.",
)
@limiter.limit("10/minute")
async def trigger_redaction(
    request: Request,
    redact_request: RedactRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_optional_user),
) -> dict:
    try:
        try:
            doc_id = redact_request.doc_id if isinstance(redact_request.doc_id, UUID) else UUID(str(redact_request.doc_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format",
            )

        result = await db.execute(
            select(DocumentJob).where(DocumentJob.id == doc_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            logger.warning(f"Redaction request for non-existent job: {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {redact_request.doc_id} not found",
            )

        valid_statuses = {JobStatus.PII_DETECTED.value, JobStatus.COMPLETED.value}
        if job.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document is not ready for redaction. Current status: {job.status}. "
                f"Redaction can only be applied after PII detection completes.",
            )
        
        # Prevent concurrent redactions (check if already REDACTING)
        if job.status == JobStatus.REDACTING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is already being redacted. Please wait for the current redaction to complete.",
            )

        logger.info(f"Redaction request: job_id={job.id}, level={redact_request.redaction_level}")

        # Write audit log using existing db session
        audit_log = AuditLog(
            job_id=job.id,
            action=AuditAction.REDACT.value,
            actor=user_id or "anonymous",
            details={"redaction_level": redact_request.redaction_level},
            ip_address=request.client.host if request.client else None,
            timestamp=datetime.utcnow(),
        )
        db.add(audit_log)
        await db.commit()

        # Enqueue redaction task
        redact_document_task.apply_async(
            args=[str(job.id), redact_request.redaction_level],
            countdown=1,
        )

        logger.info(f"Redaction task enqueued for job {job.id}")

        return {
            "message": "Redaction started",
            "doc_id": str(job.id),
            "redaction_level": redact_request.redaction_level,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redaction request failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start redaction",
        )