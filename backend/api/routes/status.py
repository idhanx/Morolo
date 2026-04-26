"""Status endpoint for job polling."""

import logging
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware import limiter
from backend.api.schemas import PIIEntitySchema, StatusResponse
from backend.core.database import get_db
from backend.models.db_models import DocumentJob, PIIEntity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["status"])


@router.get(
    "/{doc_id}",
    response_model=StatusResponse,
    summary="Get document processing status",
    description="Poll document processing status. Returns job status, PII summary, and download URLs when available.",
)
@limiter.limit("100/minute")  # Rate limit: 100 status checks per minute per IP
async def get_document_status(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    """
    Get document processing status.

    Returns:
    - Job status (PENDING, EXTRACTING, PII_DETECTING, PII_DETECTED, REDACTING, COMPLETED, FAILED)
    - PII entity summary (counts by type)
    - Risk score and band (when available)
    - Download URLs (when available)
    - OpenMetadata entity FQN (when available)

    Args:
        request: FastAPI request (for rate limiting)
        doc_id: Document job UUID
        db: Database session

    Returns:
        StatusResponse: Job status and details

    Raises:
        HTTPException 404: Document not found
    """
    try:
        # Parse doc_id
        try:
            job_id = UUID(doc_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format",
            )

        # Fetch job
        result = await db.execute(
            select(DocumentJob).where(DocumentJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {doc_id} not found",
            )

        # Fetch PII entities
        pii_result = await db.execute(
            select(PIIEntity).where(PIIEntity.job_id == job.id)
        )
        pii_entities = pii_result.scalars().all()

        # Build PII summary (counts by type)
        pii_summary = defaultdict(int)
        for entity in pii_entities:
            pii_summary[entity.entity_type] += 1

        # Convert PII entities to schema
        pii_entities_schema = [
            PIIEntitySchema(
                entity_type=e.entity_type,
                start_offset=e.start_offset,
                end_offset=e.end_offset,
                confidence=e.confidence,
                subtype=e.subtype,
            )
            for e in pii_entities
        ]

        # Get download URLs from storage (if available)
        original_url = None
        redacted_url = None

        if job.storage_key:
            from backend.core.storage import get_storage_client
            import asyncio

            storage = get_storage_client()
            try:
                original_url = await asyncio.to_thread(
                    storage.generate_presigned_url, job.storage_key, 3600
                )
            except Exception as e:
                logger.warning(f"Failed to generate presigned URL: {e}")

        if job.details and job.details.get("redacted_storage_key"):
            from backend.core.storage import get_storage_client
            import asyncio

            storage = get_storage_client()
            try:
                redacted_url = await asyncio.to_thread(
                    storage.generate_presigned_url,
                    job.details["redacted_storage_key"],
                    3600,
                )
            except Exception as e:
                logger.warning(f"Failed to generate redacted presigned URL: {e}")

        # Get OpenMetadata entity FQNs
        om_entity_fqn = None
        redacted_om_entity_fqn = None
        if job.details:
            om_entity_fqn = job.details.get("om_entity_fqn")
            redacted_om_entity_fqn = job.details.get("om_redacted_entity_fqn")

        # Build response
        response = StatusResponse(
            doc_id=str(job.id),
            filename=job.filename,
            status=job.status,
            risk_score=job.risk_score,
            risk_band=job.risk_band,
            pii_summary=dict(pii_summary),
            pii_entities=pii_entities_schema,
            created_at=job.created_at,
            updated_at=job.updated_at,
            original_url=original_url,
            redacted_url=redacted_url,
            om_entity_fqn=om_entity_fqn,
            redacted_om_entity_fqn=redacted_om_entity_fqn,
            error=job.details.get("error") if job.details else None,
            details=job.details,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed for {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document status",
        )
