"""Morolo FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.middleware import configure_middleware
from backend.api.routes import audit, health, redact, risk, status, upload
from backend.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup:
    - Run database migrations
    - Validate OM connectivity
    - Register morolo-docs CustomStorage service in OM
    - Ensure DPDP Act policy exists

    Shutdown:
    - Clean up resources
    """
    # Startup
    logger.info("Morolo starting up...")

    # Auto-run database migrations
    try:
        logger.info("Running database migrations...")
        from alembic.config import Config
        from alembic.command import upgrade
        import os
        
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
        upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        logger.warning("Continuing startup despite migration failure (may impact functionality)")

    try:
        from backend.services.om_integration import OMIntegrationService

        om_service = OMIntegrationService()

        # Full bootstrap: storage service + nested tags + custom properties + pipeline (all gaps)
        try:
            om_service.bootstrap()
        except Exception as e:
            logger.warning(f"OM bootstrap failed (non-fatal): {e}")

        # Ensure DPDP policy exists
        try:
            policy_id = om_service.ensure_dpdp_policy()
            logger.info(f"DPDP policy ready: {policy_id}")
        except Exception as e:
            logger.warning(f"DPDP policy setup failed (non-fatal): {e}")

        # Store OM service in app state for reuse
        app.state.om_service = om_service

    except Exception as e:
        logger.warning(f"OM initialization failed (non-fatal): {e}")

    logger.info("Morolo startup complete")

    yield

    # Shutdown
    logger.info("Morolo shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="Morolo",
        description=(
            "Document-level PII governance extension for OpenMetadata. "
            "Detects PII in PDFs, DOCX, and images, applies redaction, "
            "and creates Container entities with classification tags and lineage in OpenMetadata."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure middleware (CORS, rate limiting, logging)
    configure_middleware(app)

    # Include routers
    app.include_router(upload.router)
    app.include_router(redact.router)
    app.include_router(status.router)
    app.include_router(risk.router)
    app.include_router(audit.router)
    app.include_router(health.router)

    # Add global exception handler for standardized error responses
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Standardize all HTTP exception responses."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle unexpected exceptions with standardized response."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "status_code": 500,
                "path": str(request.url.path),
            },
        )

    logger.info("FastAPI app created with all routes")

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
