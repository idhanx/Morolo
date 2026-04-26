"""Application configuration using pydantic-settings."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://morolo:morolo_password@localhost:5432/morolo_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO / S3 Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_PUBLIC_ENDPOINT: str = ""  # Public URL for presigned URLs (e.g. localhost:9000)
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "morolo-documents"
    MINIO_SECURE: bool = False
    STORAGE_BACKEND: str = "minio"  # Options: minio, local

    # Local Storage
    LOCAL_STORAGE_PATH: str = "./storage"

    # OpenMetadata
    OM_HOST: str = "http://localhost:8585"
    OM_TOKEN: str = ""
    OM_API_VERSION: str = "v1"

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # File Upload Limits (bytes)
    MAX_FILE_SIZE_PDF: int = 10485760  # 10 MB
    MAX_FILE_SIZE_IMAGE: int = 5242880  # 5 MB
    MAX_FILE_SIZE_DOCX: int = 10485760  # 10 MB

    # OCR Configuration
    OCR_CHAR_THRESHOLD: int = 100
    TESSERACT_CMD: str = "/usr/bin/tesseract"

    # PII Detection
    PII_CONFIDENCE_THRESHOLD: float = 0.7

    # Rate Limiting
    RATE_LIMIT_UPLOADS_PER_MINUTE: int = 10
    RATE_LIMIT_STATUS_PER_MINUTE: int = 100

    # Celery (derived from REDIS_URL if not explicitly set)
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # Circuit Breaker
    CIRCUIT_BREAKER_FAIL_MAX: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = 60

    # Development
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Frontend URLs
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    NEXT_PUBLIC_OM_UI_URL: str = "http://localhost:8585"

    @model_validator(mode="after")
    def set_celery_urls(self) -> "Settings":
        """Derive Celery broker/backend from REDIS_URL if not explicitly provided."""
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        return self

    @model_validator(mode="after")
    def set_minio_public_endpoint(self) -> "Settings":
        """Default MINIO_PUBLIC_ENDPOINT to MINIO_ENDPOINT if not explicitly set."""
        if not self.MINIO_PUBLIC_ENDPOINT:
            self.MINIO_PUBLIC_ENDPOINT = self.MINIO_ENDPOINT
        return self

    @model_validator(mode="after")
    def validate_critical_config(self) -> "Settings":
        """Validate critical configuration on startup."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Check OM configuration
        if self.OM_HOST and not self.OM_TOKEN:
            logger.warning(
                "OpenMetadata host is set but OM_TOKEN is empty. "
                "OM features (classification, lineage, policies) will be disabled. "
                "Set OM_TOKEN environment variable to enable OM integration."
            )
        
        # Check JWT secret is not default
        if self.JWT_SECRET_KEY == "change-this-secret-key-in-production" and not self.DEBUG:
            logger.error(
                "CRITICAL: JWT_SECRET_KEY is using default value in production mode. "
                "Set JWT_SECRET_KEY environment variable immediately."
            )
        
        return self


# Global settings instance
settings = Settings()