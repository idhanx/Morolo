"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from backend.core.types import JobStatus, RedactionLevel, RiskBand


class UploadResponse(BaseModel):
    """Response model for document upload."""

    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: JobStatus = Field(..., description="Initial processing status")
    message: str = Field(..., description="Human-readable status message")


class PIIEntitySchema(BaseModel):
    """Schema for a detected PII entity."""

    entity_type: str = Field(..., description="Type of PII (e.g., AADHAAR, PAN, EMAIL)")
    start_offset: int = Field(..., ge=0, description="Start position in text")
    end_offset: int = Field(..., ge=0, description="End position in text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    subtype: str | None = Field(None, description="Entity subtype (e.g., IndianGovtID)")

    @field_validator("end_offset")
    @classmethod
    def validate_end_offset(cls, v, info):
        """Ensure end_offset > start_offset."""
        if "start_offset" in info.data and v <= info.data["start_offset"]:
            raise ValueError("end_offset must be greater than start_offset")
        return v


class StatusResponse(BaseModel):
    """Response model for document processing status."""

    doc_id: UUID
    filename: str
    status: JobStatus
    risk_score: float | None = Field(None, ge=0.0, le=100.0)
    risk_band: RiskBand | None = None
    pii_summary: dict[str, int] = Field(
        default_factory=dict, description="Count of PII entities by type"
    )
    pii_entities: list[PIIEntitySchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    om_entity_fqn: str | None = Field(None, description="OpenMetadata Container FQN")
    redacted_om_entity_fqn: str | None = Field(
        None, description="OpenMetadata redacted Container FQN"
    )
    original_url: str | None = Field(None, description="Presigned URL for original document")
    redacted_url: str | None = Field(None, description="Presigned URL for redacted document")
    error: str | None = Field(None, description="Error message if processing failed")
    details: dict[str, Any] | None = Field(None, description="Processing details including extracted text")


class RedactRequest(BaseModel):
    """Request model for document redaction."""

    doc_id: UUID = Field(..., description="Document ID to redact")
    redaction_level: RedactionLevel = Field(..., description="Redaction strategy to apply")


class RiskScoreResponse(BaseModel):
    """Response model for document risk score."""

    doc_id: UUID
    filename: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_band: RiskBand
    pii_breakdown: dict[str, dict[str, Any]] = Field(
        ...,
        description="PII type breakdown with count and avg confidence per type",
    )
    total_entities: int = Field(..., ge=0)


class PIIInstanceRecord(BaseModel):
    """Record of a single PII instance for redaction metadata."""

    entity_type: str
    original_value: str
    redacted_value: str
    start_offset: int
    end_offset: int
    confidence: float


class RedactionMetadata(BaseModel):
    """Complete metadata for a redaction operation."""

    document_id: UUID
    filename: str
    redaction_level: RedactionLevel
    timestamp: datetime
    pii_instances: list[PIIInstanceRecord] = Field(
        ..., min_length=0, description="List of redacted PII instances"
    )
    total_entities_redacted: int = Field(..., ge=0)
    risk_score_before: float = Field(..., ge=0.0, le=100.0)
    risk_score_after: float = Field(..., ge=0.0, le=100.0)


class AuditLogResponse(BaseModel):
    """Response model for audit log entries."""

    id: UUID
    job_id: UUID
    action: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    timestamp: datetime
