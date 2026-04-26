"""Upload endpoint for document ingestion."""

import hashlib
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_optional_user
from backend.api.file_validation import validate_file
from backend.api.middleware import limiter
from backend.api.schemas import UploadResponse
from backend.core.database import get_db
from backend.core.storage import get_storage_client
from backend.core.types import AuditAction, JobStatus
from backend.models.db_models import AuditLog, DocumentJob
from backend.tasks.audit import log_action
from backend.tasks.processing_tasks import extract_text_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload document for PII analysis",
    description="Upload a document (PDF, DOCX, or image) for PII detection and redaction. "
    "Returns immediately with job ID. Use /status/{doc_id} to poll for completion.",
)
@limiter.limit("10/minute")  # Rate limit: 10 uploads per minute per IP
async def upload_document(
    request: Request,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_optional_user),
) -> UploadResponse:
    """
    Upload document for PII analysis.

    Pipeline:
    1. Validate file (extension, size, magic bytes)
    2. Compute SHA-256 hash
    3. Check for duplicate (return existing job if hash matches)
    4. Upload to storage
    5. Create DocumentJob in database
    6. Enqueue extract_text_task
    7. Write audit log
    8. Return 202 with job ID

    Args:
        request: FastAPI request (for rate limiting)
        file: Uploaded file
        db: Database session
        user_id: Authenticated user ID (optional)

    Returns:
        UploadResponse: Job ID and status

    Raises:
        HTTPException 400: Invalid file
        HTTPException 413: File too large
        HTTPException 415: Unsupported file type
    """
    try:
        # Validate file
        file_bytes = await validate_file(file)

        # Compute SHA-256 hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        logger.info(
            f"Upload request: filename={file.filename}, "
            f"size={len(file_bytes)}, hash={file_hash[:16]}..."
        )

        # Check for duplicate
        result = await db.execute(
            select(DocumentJob).where(DocumentJob.file_hash == file_hash)
        )
        existing_job = result.scalar_one_or_none()

        if existing_job:
            logger.info(
                f"Duplicate file detected: {file_hash[:16]}... "
                f"(existing job: {existing_job.id})"
            )

            return UploadResponse(
                doc_id=str(existing_job.id),
                filename=existing_job.filename,
                status=existing_job.status,
                message="File already uploaded. Returning existing job.",
            )

        # Generate job ID and storage key with sanitized filename
        from urllib.parse import quote
        job_id = uuid4()
        # Sanitize filename to prevent path traversal
        sanitized_filename = quote(file.filename or "document", safe=".-_")
        storage_key = f"documents/{job_id}/{sanitized_filename}"

        # Upload to storage
        storage = get_storage_client()
        import asyncio
        await asyncio.to_thread(
            storage.upload_file,
            storage_key,
            file_bytes,
            file.content_type or "application/octet-stream",
        )

        logger.info(f"File uploaded to storage: {storage_key}")

        # Create DocumentJob
        job = DocumentJob(
            id=job_id,
            filename=file.filename or "unknown",
            file_size=len(file_bytes),
            file_hash=file_hash,
            content_type=file.content_type or "application/octet-stream",
            storage_key=storage_key,
            status=JobStatus.PENDING.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)

        logger.info(f"DocumentJob created: {job.id}")

        # Write audit log
        await log_action(
            job_id=job.id,
            action=AuditAction.UPLOAD,
            actor=user_id or "anonymous",
            details={
                "filename": file.filename,
                "file_size": len(file_bytes),
                "file_hash": file_hash,
            },
            ip_address=request.client.host if request.client else None,
        )

        # Enqueue text extraction task
        extract_text_task.apply_async(args=[str(job.id)], countdown=1)

        logger.info(f"Text extraction task enqueued for job {job.id}")

        return UploadResponse(
            doc_id=str(job.id),
            filename=job.filename,
            status=job.status,
            message="Document uploaded successfully. Processing started.",
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise
