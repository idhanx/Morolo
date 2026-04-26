/**
 * TypeScript interfaces mirroring backend Pydantic schemas.
 */

export type JobStatus =
    | "PENDING"
    | "EXTRACTING"
    | "PII_DETECTING"
    | "PII_DETECTED"
    | "REDACTING"
    | "COMPLETED"
    | "FAILED";

export type RedactionLevel = "LIGHT" | "FULL" | "SYNTHETIC";

export type RiskBand = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type AuditAction =
    | "UPLOAD"
    | "EXTRACT_TEXT"
    | "DETECT_PII"
    | "REDACT"
    | "INGEST_TO_OM"
    | "APPLY_TAGS"
    | "CREATE_LINEAGE"
    | "APPLY_POLICY"
    | "PROCESS"
    | "DOWNLOAD"
    | "FAILED";

export interface PIIEntity {
    entity_type: string;
    start_offset: number;
    end_offset: number;
    confidence: number;
    subtype: string | null;
}

export interface UploadResponse {
    doc_id: string;
    filename: string;
    status: JobStatus;
    message: string;
}

export interface StatusResponse {
    doc_id: string;
    filename: string;
    status: JobStatus;
    risk_score: number | null;
    risk_band: RiskBand | null;
    pii_summary: Record<string, number>;
    pii_entities: PIIEntity[];
    created_at: string;
    updated_at: string;
    om_entity_fqn: string | null;
    redacted_om_entity_fqn: string | null;
    original_url: string | null;
    redacted_url: string | null;
    error: string | null;
}

export interface RedactRequest {
    doc_id: string;
    redaction_level: RedactionLevel;
}

export interface RiskScoreResponse {
    doc_id: string;
    filename: string;
    risk_score: number;
    risk_band: RiskBand;
    pii_breakdown: Record<string, { count: number; avg_confidence: number }>;
    total_entities: number;
}

export interface AuditLogResponse {
    id: string;
    job_id: string;
    action: AuditAction;
    actor: string;
    details: Record<string, unknown>;
    ip_address: string | null;
    timestamp: string;
}

/** Terminal statuses — polling should stop */
export const TERMINAL_STATUSES: JobStatus[] = ["COMPLETED", "FAILED"];

/** Risk band color mapping */
export const RISK_BAND_COLORS: Record<RiskBand, string> = {
    LOW: "bg-green-100 text-green-800",
    MEDIUM: "bg-yellow-100 text-yellow-800",
    HIGH: "bg-orange-100 text-orange-800",
    CRITICAL: "bg-red-100 text-red-800",
};

/** PII entity highlight colors */
export const PII_ENTITY_COLORS: Record<string, string> = {
    AADHAAR: "bg-red-200",
    PAN: "bg-orange-200",
    DRIVING_LICENSE: "bg-yellow-200",
    EMAIL_ADDRESS: "bg-blue-200",
    PHONE_NUMBER: "bg-purple-200",
    PERSON: "bg-green-200",
};
