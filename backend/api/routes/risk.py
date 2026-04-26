"""Risk score endpoint."""

import logging
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware import limiter
from backend.api.schemas import RiskScoreResponse
from backend.core.database import get_db
from backend.models.db_models import DocumentJob, PIIEntity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk-score", tags=["risk"])


@router.get(
    "/{doc_id}",
    response_model=RiskScoreResponse,
    summary="Get document risk score",
    description="Get the PII risk score and breakdown for a document. "
    "Only available after PII detection completes.",
)
@limiter.limit("100/minute")
async def get_risk_score(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> RiskScoreResponse:
    """
    Get document risk score and PII breakdown.

    Args:
        request: FastAPI request (for rate limiting)
        doc_id: Document job UUID
        db: Database session

    Returns:
        RiskScoreResponse: Risk score, band, and per-type breakdown

    Raises:
        HTTPException 404: Document not found
        HTTPException 400: PII detection not yet complete
    """
    try:
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

        if job.risk_score is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Risk score not yet available. Current status: {job.status}",
            )

        # Fetch PII entities for breakdown
        pii_result = await db.execute(
            select(PIIEntity).where(PIIEntity.job_id == job.id)
        )
        pii_entities = pii_result.scalars().all()

        # Build per-type breakdown: {type: {count, avg_confidence}}
        type_data: dict = defaultdict(lambda: {"count": 0, "total_confidence": 0.0})
        for entity in pii_entities:
            type_data[entity.entity_type]["count"] += 1
            type_data[entity.entity_type]["total_confidence"] += entity.confidence

        pii_breakdown = {
            entity_type: {
                "count": data["count"],
                "avg_confidence": round(
                    data["total_confidence"] / data["count"], 3
                ) if data["count"] > 0 else 0.0,
            }
            for entity_type, data in type_data.items()
        }

        return RiskScoreResponse(
            doc_id=str(job.id),
            filename=job.filename,
            risk_score=job.risk_score,
            risk_band=job.risk_band,
            total_entities=len(pii_entities),
            pii_breakdown=pii_breakdown,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk score retrieval failed for {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve risk score",
        )
