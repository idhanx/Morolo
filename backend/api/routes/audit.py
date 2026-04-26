"""Audit log endpoint."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware import limiter
from backend.api.schemas import AuditLogResponse
from backend.core.database import get_db
from backend.models.db_models import AuditLog, DocumentJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/{doc_id}",
    response_model=list[AuditLogResponse],
    summary="Get document audit log",
    description="Get the audit trail for a document, ordered by timestamp ascending.",
)
@limiter.limit("100/minute")
async def get_audit_log(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogResponse]:
    """
    Get audit log for a document.

    Returns all audit events for the document in chronological order:
    - UPLOAD: Document uploaded
    - PROCESS: Processing steps (extract, detect, redact)
    - INGEST: OpenMetadata ingestion
    - REDACT: Redaction applied
    - APPLY_POLICY: Policy enforcement verified

    Args:
        request: FastAPI request (for rate limiting)
        doc_id: Document job UUID
        db: Database session

    Returns:
        list[AuditLogResponse]: Audit events ordered by timestamp

    Raises:
        HTTPException 404: Document not found
    """
    try:
        try:
            job_id = UUID(doc_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format",
            )

        # Verify job exists
        result = await db.execute(
            select(DocumentJob).where(DocumentJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {doc_id} not found",
            )

        # Fetch audit logs ordered by timestamp ascending
        audit_result = await db.execute(
            select(AuditLog)
            .where(AuditLog.job_id == job_id)
            .order_by(AuditLog.timestamp.asc())
        )
        audit_logs = audit_result.scalars().all()

        return [
            AuditLogResponse(
                id=str(log.id),
                job_id=str(log.job_id),
                action=log.action,
                actor=log.actor,
                details=log.details,
                ip_address=log.ip_address,
                timestamp=log.timestamp,
            )
            for log in audit_logs
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit log retrieval failed for {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log",
        )
