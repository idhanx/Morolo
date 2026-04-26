"""SQLAlchemy ORM models for Morolo database."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class DocumentJob(Base):
    """Document processing job tracking."""

    __tablename__ = "document_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    scan_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_band: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    om_entity_fqn: Mapped[str | None] = mapped_column(String(500), nullable=True)
    redacted_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    redacted_om_entity_fqn: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Flexible JSON store for task pipeline data (extracted text, entity counts, errors, etc.)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=None)
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.utcnow()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )
    
    # Relationships
    pii_entities: Mapped[list["PIIEntity"]] = relationship(
        "PIIEntity", back_populates="document_job", cascade="all, delete-orphan"
    )
    redaction_reports: Mapped[list["RedactionReport"]] = relationship(
        "RedactionReport", back_populates="document_job", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="document_job", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_document_jobs_status_created", "status", "created_at"),
        Index("idx_document_jobs_risk_band", "risk_band"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="check_risk_score_range"),
    )


class PIIEntity(Base):
    """Detected PII entity in a document."""

    __tablename__ = "pii_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_jobs.id", ondelete="CASCADE"), nullable=False
    )
    
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subtype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.utcnow()
    )
    
    # Relationships
    document_job: Mapped["DocumentJob"] = relationship("DocumentJob", back_populates="pii_entities")
    
    __table_args__ = (
        Index("idx_pii_entities_job_type", "job_id", "entity_type"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="check_confidence_range"),
        CheckConstraint("start_offset >= 0", name="check_start_offset_positive"),
        CheckConstraint("end_offset > start_offset", name="check_end_after_start"),
    )


class RedactionReport(Base):
    """Redaction operation report."""

    __tablename__ = "redaction_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_jobs.id", ondelete="CASCADE"), nullable=False
    )
    
    redaction_level: Mapped[str] = mapped_column(String(50), nullable=False)
    total_entities_redacted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_score_before: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score_after: Mapped[float] = mapped_column(Float, nullable=False)
    redacted_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    report_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.utcnow()
    )
    
    # Relationships
    document_job: Mapped["DocumentJob"] = relationship(
        "DocumentJob", back_populates="redaction_reports"
    )
    
    __table_args__ = (
        Index("idx_redaction_reports_job_created", "job_id", "created_at"),
        CheckConstraint(
            "risk_score_before >= 0 AND risk_score_before <= 100",
            name="check_risk_before_range",
        ),
        CheckConstraint(
            "risk_score_after >= 0 AND risk_score_after <= 100", name="check_risk_after_range"
        ),
        CheckConstraint("total_entities_redacted >= 0", name="check_entities_positive"),
    )


class AuditLog(Base):
    """Audit log for document operations."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_jobs.id", ondelete="CASCADE"), nullable=False
    )
    
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.utcnow(), index=True
    )
    
    # Relationships
    document_job: Mapped["DocumentJob"] = relationship("DocumentJob", back_populates="audit_logs")
    
    __table_args__ = (
        Index("idx_audit_logs_job_timestamp", "job_id", "timestamp"),
        Index("idx_audit_logs_action_timestamp", "action", "timestamp"),
    )
