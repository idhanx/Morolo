/**
 * React Query hooks for all API endpoints.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
    getAuditLog,
    getDocumentStatus,
    getRiskScore,
    triggerRedaction,
    uploadDocument,
} from "@/lib/api";
import type { RedactionLevel, StatusResponse } from "@/types/api";
import { TERMINAL_STATUSES } from "@/types/api";

/** Query keys */
export const queryKeys = {
    status: (docId: string) => ["status", docId] as const,
    riskScore: (docId: string) => ["riskScore", docId] as const,
    auditLog: (docId: string) => ["auditLog", docId] as const,
};

/**
 * Upload document mutation.
 */
export function useUploadMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: uploadDocument,
        onSuccess: (data) => {
            // Pre-populate status cache
            queryClient.setQueryData(queryKeys.status(data.doc_id), {
                doc_id: data.doc_id,
                filename: data.filename,
                status: data.status,
                risk_score: null,
                risk_band: null,
                pii_summary: {},
                pii_entities: [],
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                om_entity_fqn: null,
                redacted_om_entity_fqn: null,
                original_url: null,
                redacted_url: null,
                error: null,
            } satisfies StatusResponse);
        },
    });
}

/**
 * Poll document status every 3 seconds until terminal state.
 */
export function useDocumentStatus(docId: string | null) {
    return useQuery({
        queryKey: queryKeys.status(docId ?? ""),
        queryFn: () => getDocumentStatus(docId!),
        enabled: !!docId,
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            if (!status || TERMINAL_STATUSES.includes(status)) {
                return false; // Stop polling
            }
            return 3000; // Poll every 3 seconds
        },
        staleTime: 0,
    });
}

/**
 * Get risk score — only enabled when PII detection is complete.
 */
export function useRiskScore(docId: string | null, status: string | null) {
    return useQuery({
        queryKey: queryKeys.riskScore(docId ?? ""),
        queryFn: () => getRiskScore(docId!),
        enabled: !!docId && (status === "PII_DETECTED" || status === "COMPLETED"),
        staleTime: 60_000, // Cache for 1 minute
    });
}

/**
 * Trigger redaction mutation.
 */
export function useRedactMutation(docId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (level: RedactionLevel) =>
            triggerRedaction({ doc_id: docId, redaction_level: level }),
        onSuccess: () => {
            // Invalidate status to trigger re-poll
            queryClient.invalidateQueries({ queryKey: queryKeys.status(docId) });
        },
    });
}

/**
 * Get audit log — polls while job is non-terminal.
 */
export function useAuditLog(docId: string | null, status: string | null) {
    return useQuery({
        queryKey: queryKeys.auditLog(docId ?? ""),
        queryFn: () => getAuditLog(docId!),
        enabled: !!docId,
        refetchInterval: () => {
            if (!status || TERMINAL_STATUSES.includes(status as any)) {
                return false;
            }
            return 5000; // Poll every 5 seconds while processing
        },
        staleTime: 0,
    });
}
