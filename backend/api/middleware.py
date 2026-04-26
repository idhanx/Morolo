"""FastAPI middleware configuration."""

import logging
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Context variable for request tracing
request_id_context: ContextVar[str] = ContextVar("request_id", default="")

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP address
    default_limits=[],  # No default limits (set per-route)
    storage_uri=settings.REDIS_URL,  # Use Redis for distributed rate limiting
)


def configure_middleware(app: FastAPI) -> None:
    """
    Configure FastAPI middleware.

    Adds:
    - Request ID tracing (X-Request-ID header)
    - Rate limiting (slowapi)
    - CORS middleware
    - Request logging

    Args:
        app: FastAPI application instance
    """
    # Add rate limiter to app state
    app.state.limiter = limiter

    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Next.js dev server
            "http://localhost:8000",  # FastAPI dev server
            settings.NEXT_PUBLIC_API_URL,  # Production frontend
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware (for tracing)
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add request ID from header or generate new one for tracing."""
        # Check for X-Request-ID header
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_context.set(req_id)
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests with request ID."""
        req_id = request_id_context.get()
        logger.info(f"[{req_id}] {request.method} {request.url.path}")

        response = await call_next(request)

        logger.info(
            f"[{req_id}] {request.method} {request.url.path} - {response.status_code}"
        )

        return response

    logger.info("Middleware configured")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.

    Returns 429 with Retry-After header.

    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception

    Returns:
        Response: 429 Too Many Requests with Retry-After header
    """
    # Extract retry-after from exception
    retry_after = 60  # Default: 60 seconds

    response = Response(
        content='{"detail": "Rate limit exceeded. Please try again later."}',
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        media_type="application/json",
    )

    response.headers["Retry-After"] = str(retry_after)

    logger.warning(
        f"Rate limit exceeded for {get_remote_address(request)} "
        f"on {request.url.path}"
    )

    return response
