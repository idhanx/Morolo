"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { StatusIndicator } from "@/components/shared/StatusIndicator";
import { DocumentViewer } from "@/components/document/DocumentViewer";
import { RiskScoreCard } from "@/components/risk/RiskScoreCard";
import { RedactionControls } from "@/components/redaction/RedactionControls";
import { LineageGraph } from "@/components/lineage/LineageGraph";
import { ActivityTimeline } from "@/components/activity/ActivityTimeline";
import { useDocumentStatus, useRiskScore, useAuditLog } from "@/lib/queries";

const OM_UI_URL = process.env.NEXT_PUBLIC_OM_UI_URL || "http://localhost:8585";

interface PageProps {
  params: { docId: string };
}

export default function DocumentDetailPage({ params }: PageProps) {
  const { docId } = params;

  const { data: status, isLoading: statusLoading } = useDocumentStatus(docId);
  const { data: riskScore, isLoading: riskLoading } = useRiskScore(
    docId,
    status?.status ?? null
  );
  const { data: auditLogs, isLoading: auditLoading } = useAuditLog(
    docId,
    status?.status ?? null
  );

  const extractedText = (status as any)?.details?.extracted_text ?? "";
  const charCount = (status as any)?.details?.char_count ?? extractedText.length;

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="w-4 h-4" />
              Upload another
            </Link>
            <span className="text-gray-300">|</span>
            <h1 className="text-lg font-semibold text-gray-900 truncate max-w-xs">
              {status?.filename ?? docId}
            </h1>
          </div>

          {/* OM deep-link */}
          {status?.om_entity_fqn && (
            <a
              href={`${OM_UI_URL}/container/${encodeURIComponent(status.om_entity_fqn)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline"
            >
              <ExternalLink className="w-4 h-4" />
              View in OpenMetadata
            </a>
          )}
        </div>

        {/* Status stepper */}
        <div className="bg-white rounded-xl border p-6">
          {statusLoading ? (
            <div className="h-12 bg-gray-100 rounded animate-pulse" />
          ) : status ? (
            <StatusIndicator status={status.status} error={status.error} />
          ) : null}
        </div>

        {/* Main content grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Document viewer */}
          <div className="lg:col-span-2 space-y-4">
            <DocumentViewer
              text={extractedText}
              entities={status?.pii_entities ?? []}
              isLoading={statusLoading || status?.status === "EXTRACTING"}
              charCount={charCount}
            />

            {/* PII summary table */}
            {status && Object.keys(status.pii_summary).length > 0 && (
              <div className="bg-white rounded-lg border p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">PII Summary</h3>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(status.pii_summary).map(([type, count]) => (
                    <div
                      key={type}
                      className="flex justify-between text-sm px-3 py-1.5 bg-gray-50 rounded"
                    >
                      <span className="text-gray-600">{type}</span>
                      <span className="font-medium text-gray-900">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Risk + Redaction + Activity */}
          <div className="space-y-4">
            <RiskScoreCard data={riskScore} isLoading={riskLoading} />

            {status && (
              <RedactionControls
                docId={docId}
                status={status.status}
                redactedUrl={status.redacted_url}
              />
            )}

            {/* Activity timeline */}
            <div className="bg-white rounded-lg border p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Activity</h3>
              <ActivityTimeline
                logs={auditLogs ?? []}
                isLoading={auditLoading}
              />
            </div>
          </div>
        </div>

        {/* Lineage */}
        {(status?.om_entity_fqn || status?.redacted_om_entity_fqn) && (
          <LineageGraph
            originalFqn={status.om_entity_fqn}
            redactedFqn={status.redacted_om_entity_fqn}
            omUiUrl={OM_UI_URL}
          />
        )}
      </div>
    </main>
  );
}