"""Core type definitions and enumerations for Morolo."""

from enum import Enum


class JobStatus(str, Enum):
    """Document processing job status."""

    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    PII_DETECTING = "PII_DETECTING"
    PII_DETECTED = "PII_DETECTED"
    REDACTING = "REDACTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RedactionLevel(str, Enum):
    """Redaction strategy level."""

    LIGHT = "LIGHT"  # Preserve first 2 + last 2 chars, mask middle
    FULL = "FULL"  # Replace entire value with [REDACTED]
    SYNTHETIC = "SYNTHETIC"  # Replace with format-matching fake value


class RiskBand(str, Enum):
    """Risk classification bands based on PII risk score."""

    LOW = "LOW"  # 0-25
    MEDIUM = "MEDIUM"  # 26-50
    HIGH = "HIGH"  # 51-75
    CRITICAL = "CRITICAL"  # 76-100


class ScanType(str, Enum):
    """Document scan type classification."""

    TEXT = "TEXT"  # Text-based PDF (extractable text)
    SCANNED = "SCANNED"  # Image-based PDF (requires OCR)
    MIXED = "MIXED"  # Contains both text and scanned pages


class AuditAction(str, Enum):
    """Audit log action types."""

    UPLOAD = "UPLOAD"
    EXTRACT_TEXT = "EXTRACT_TEXT"
    DETECT_PII = "DETECT_PII"
    REDACT = "REDACT"
    INGEST_TO_OM = "INGEST_TO_OM"
    APPLY_TAGS = "APPLY_TAGS"
    CREATE_LINEAGE = "CREATE_LINEAGE"
    APPLY_POLICY = "APPLY_POLICY"
    PROCESS = "PROCESS"
    DOWNLOAD = "DOWNLOAD"
    FAILED = "FAILED"
