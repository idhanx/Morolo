"""Health check endpoint."""

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text

from backend.core.config import settings
from backend.core.database import async_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    summary="Health check",
    description="Check connectivity to all dependencies: PostgreSQL, Redis, MinIO, and OpenMetadata.",
)
async def health_check() -> dict:
    """
    Check health of all system dependencies.

    Returns structured status for each dependency:
    - postgres: Database connectivity
    - redis: Cache/broker connectivity
    - minio: Object storage connectivity
    - openmetadata: OM API connectivity

    Returns:
        dict: Health status for each dependency
    """
    results = {
        "status": "healthy",
        "dependencies": {},
    }

    # Check PostgreSQL
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        results["dependencies"]["postgres"] = {"status": "healthy"}
    except Exception as e:
        logger.warning(f"PostgreSQL health check failed: {e}")
        results["dependencies"]["postgres"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        results["status"] = "degraded"

    # Check Redis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.aclose()
        results["dependencies"]["redis"] = {"status": "healthy"}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        results["dependencies"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        results["status"] = "degraded"

    # Check MinIO
    try:
        import asyncio

        from backend.core.storage import get_storage_client

        storage = get_storage_client()
        # Try to download a non-existent key — connection works if we get a "not found" error
        await asyncio.to_thread(storage.download_file, "__health_check__")
    except Exception as e:
        # Expected: file doesn't exist, but connection worked
        error_str = str(e).lower()
        if "nosuchkey" in error_str or "not found" in error_str or "no such key" in error_str:
            results["dependencies"]["minio"] = {"status": "healthy"}
        else:
            logger.warning(f"MinIO health check failed: {e}")
            results["dependencies"]["minio"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            results["status"] = "degraded"

    # Check OpenMetadata
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.OM_HOST}/api/v1/system/status",
                headers={"Authorization": f"Bearer {settings.OM_TOKEN}"},
            )
            if response.status_code == 200:
                results["dependencies"]["openmetadata"] = {"status": "healthy"}
            else:
                results["dependencies"]["openmetadata"] = {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                }
                results["status"] = "degraded"
    except Exception as e:
        logger.warning(f"OpenMetadata health check failed: {e}")
        results["dependencies"]["openmetadata"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        results["status"] = "degraded"

    return results
