"use client";

import type { RiskBand, RiskScoreResponse } from "@/types/api";
import { RISK_BAND_COLORS } from "@/types/api";
import { cn } from "@/lib/utils";

interface RiskScoreCardProps {
  data: RiskScoreResponse | null | undefined;
  isLoading?: boolean;
}

export function RiskScoreCard({ data, isLoading }: RiskScoreCardProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border bg-white p-4 space-y-3">
        <div className="h-5 bg-gray-200 rounded animate-pulse w-1/3" />
        <div className="h-12 bg-gray-200 rounded animate-pulse w-1/2" />
        <div className="space-y-2">
          <div className="h-3 bg-gray-200 rounded anim  ate-pulse" />
          <div className="h-3 bg-gray-200 rounded animate-pulse w-4/5" />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-lg border bg-white p-4">
        <p className="text-sm text-gray-400 italic">
          Risk score will appear after PII detection completes.
        </p>
      </div>
    );
  }

  const maxCount = Math.max(
    ...Object.values(data.pii_breakdown).map((v) => v.count),
    1
  );

  return (
    <div className="rounded-lg border bg-white p-4 space-y-4">
      {/* Score header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Risk Score</h3>
        <span
          className={cn(
            "text-xs font-semibold px-2 py-1 rounded-full",
            RISK_BAND_COLORS[data.risk_band]
          )}
        >
          {data.risk_band}
        </span>
      </div>

      {/* Score value */}
      <div className="flex items-end gap-2">
        <span className="text-4xl font-bold text-gray-900">
          {data.risk_score.toFixed(1)}
        </span>
        <span className="text-sm text-gray-500 mb-1">/ 100</span>
      </div>

      {/* Score bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={cn("h-2 rounded-full transition-all", getRiskBarColor(data.risk_band))}
          style={{ width: `${data.risk_score}%` }}
        />
      </div>

      {/* PII breakdown */}
      {Object.keys(data.pii_breakdown).length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            PII Breakdown
          </p>
          {Object.entries(data.pii_breakdown).map(([type, info]) => (
            <div key={type} className="space-y-1">
              <div className="flex justify-between text-xs text-gray-600">
                <span>{type}</span>
                <span>
                  {info.count} × {(info.avg_confidence * 100).toFixed(0)}% conf
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5">
                <div
                  className="h-1.5 rounded-full bg-blue-400"
                  style={{ width: `${(info.count / maxCount) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400">
        {data.total_entities} total PII entities detected
      </p>
    </div>
  );
}

function getRiskBarColor(band: RiskBand): string {
  const colors: Record<RiskBand, string> = {
    LOW: "bg-green-500",
    MEDIUM: "bg-yellow-500",
    HIGH: "bg-orange-500",
    CRITICAL: "bg-red-500",
  };
  return colors[band];
}
