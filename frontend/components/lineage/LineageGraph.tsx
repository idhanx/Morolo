"use client";

import { ExternalLink } from "lucide-react";

interface LineageGraphProps {
  originalFqn: string | null;
  redactedFqn: string | null;
  omUiUrl?: string;
}

/**
 * Simplified lineage display — deep-links to OpenMetadata UI.
 * (React Flow lineage graph cut per hackathon scope reduction.)
 */
export function LineageGraph({ originalFqn, redactedFqn, omUiUrl }: LineageGraphProps) {
  const baseUrl = omUiUrl || process.env.NEXT_PUBLIC_OM_UI_URL || "http://localhost:8585";

  if (!originalFqn && !redactedFqn) return null;

  return (
    <div className="rounded-lg border bg-white p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-700">OpenMetadata Lineage</h3>

      <div className="flex items-center gap-3">
        {originalFqn && (
          <a
            href={`${baseUrl}/container/${encodeURIComponent(originalFqn)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:underline"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View Original in OM
          </a>
        )}

        {originalFqn && redactedFqn && (
          <span className="text-gray-400">→</span>
        )}

        {redactedFqn && (
          <a
            href={`${baseUrl}/container/${encodeURIComponent(redactedFqn)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm text-green-600 hover:underline"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View Redacted in OM
          </a>
        )}
      </div>

      <p className="text-xs text-gray-400">
        Full lineage graph available in the OpenMetadata UI.
      </p>
    </div>
  );
}
