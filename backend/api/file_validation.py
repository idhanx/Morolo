"""File validation utilities for upload endpoints."""

import logging
from typing import Dict

from fastapi import HTTPException, UploadFile, status

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx"}

# Magic bytes for file type validation
ALLOWED_MAGIC_BYTES: Dict[str, bytes] = {
    "pdf": b"%PDF",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "docx": b"PK\x03\x04",  # ZIP signature (DOCX is a ZIP archive)
}

# File size limits by type
MAX_FILE_SIZES: Dict[str, int] = {
    "pdf": settings.MAX_FILE_SIZE_PDF,
    "png": settings.MAX_FILE_SIZE_IMAGE,
    "jpg": settings.MAX_FILE_SIZE_IMAGE,
    "jpeg": settings.MAX_FILE_SIZE_IMAGE,
    "docx": settings.MAX_FILE_SIZE_DOCX,
}


async def validate_file(upload_file: UploadFile) -> bytes:
    """
    Validate uploaded file and return file bytes.

    Validation steps:
    1. Check file extension against whitelist
    2. Read file bytes
    3. Check file size against limits
    4. Validate magic bytes (file signature)

    Args:
        upload_file: FastAPI UploadFile object

    Returns:
        bytes: File content

    Raises:
        HTTPException 400: Invalid file extension or magic bytes
        HTTPException 413: File too large
        HTTPException 415: Unsupported media type

    Example:
        @app.post("/upload")
        async def upload(file: UploadFile):
            file_bytes = await validate_file(file)
            # Process file_bytes...
    """
    # Extract filename and extension
    filename = upload_file.filename or "unknown"
    extension = None

    if "." in filename:
        extension = "." + filename.rsplit(".", 1)[1].lower()

    # Check extension whitelist
    if extension not in ALLOWED_EXTENSIONS:
        logger.warning(f"Invalid file extension: {extension} (filename: {filename})")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file bytes
    file_bytes = await upload_file.read()

    # Check file size (including zero-byte check)
    file_size = len(file_bytes)
    if file_size == 0:
        logger.warning(f"Empty file rejected: {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty. Please upload a file with content.",
        )
    
    file_type = extension.lstrip(".")
    max_size = MAX_FILE_SIZES.get(file_type, settings.MAX_FILE_SIZE_PDF)

    if file_size > max_size:
        logger.warning(
            f"File too large: {file_size} bytes (max: {max_size}, filename: {filename})"
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size for {file_type}: {max_size / 1024 / 1024:.1f} MB",
        )

    # Validate magic bytes
    expected_magic = ALLOWED_MAGIC_BYTES.get(file_type)
    if expected_magic:
        # Check if file starts with expected magic bytes
        if not file_bytes.startswith(expected_magic):
            logger.warning(
                f"Magic byte mismatch for {file_type}: "
                f"expected {expected_magic.hex()}, got {file_bytes[:8].hex()} "
                f"(filename: {filename})"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File content does not match extension. Expected {file_type} file.",
            )

    logger.info(
        f"File validated: {filename} ({file_type}, {file_size} bytes)"
    )

    return file_bytes


def get_file_extension(filename: str) -> str | None:
    """
    Extract file extension from filename.

    Args:
        filename: Filename with extension

    Returns:
        str | None: Extension (with dot) or None if no extension

    Example:
        >>> get_file_extension("document.pdf")
        ".pdf"
        >>> get_file_extension("noextension")
        None
    """
    if "." not in filename:
        return None

    return "." + filename.rsplit(".", 1)[1].lower()


def is_allowed_extension(filename: str) -> bool:
    """
    Check if filename has allowed extension.

    Args:
        filename: Filename to check

    Returns:
        bool: True if extension is allowed

    Example:
        >>> is_allowed_extension("document.pdf")
        True
        >>> is_allowed_extension("script.exe")
        False
    """
    extension = get_file_extension(filename)
    return extension in ALLOWED_EXTENSIONS
