/**
 * Axios API client with JWT interceptor and typed endpoint functions.
 */

import axios from "axios";
import type {
    AuditLogResponse,
    RedactRequest,
    RiskScoreResponse,
    StatusResponse,
    UploadResponse,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    headers: {
        "Content-Type": "application/json",
    },
});

// JWT interceptor — attach token from localStorage if present
apiClient.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("morolo_token");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});

// Response error interceptor
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Clear invalid token
            if (typeof window !== "undefined") {
                localStorage.removeItem("morolo_token");
            }
        }
        return Promise.reject(error);
    }
);

/**
 * Upload a document for PII analysis.
 */
export async function uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.post<UploadResponse>("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
    });

    return response.data;
}

/**
 * Get document processing status.
 */
export async function getDocumentStatus(docId: string): Promise<StatusResponse> {
    const response = await apiClient.get<StatusResponse>(`/status/${docId}`);
    return response.data;
}

/**
 * Get document risk score.
 */
export async function getRiskScore(docId: string): Promise<RiskScoreResponse> {
    const response = await apiClient.get<RiskScoreResponse>(`/risk-score/${docId}`);
    return response.data;
}

/**
 * Trigger document redaction.
 */
export async function triggerRedaction(request: RedactRequest): Promise<void> {
    await apiClient.post("/redact", request);
}

/**
 * Get document audit log.
 */
export async function getAuditLog(docId: string): Promise<AuditLogResponse[]> {
    const response = await apiClient.get<AuditLogResponse[]>(`/audit/${docId}`);
    return response.data;
}

/**
 * Get health status.
 */
export async function getHealth(): Promise<Record<string, unknown>> {
    const response = await apiClient.get("/health");
    return response.data;
}
