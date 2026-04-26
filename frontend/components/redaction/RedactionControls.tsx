"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Download, Shield } from "lucide-react";
import type { JobStatus, RedactionLevel } from "@/types/api";
import { useRedactMutation } from "@/lib/queries";
import { cn } from "@/lib/utils";

const REDACTION_OPTIONS: {
  value: RedactionLevel;
  label: string;
  description: string;
}[] = [
  {
    value: "LIGHT",
    label: "Light",
    description: "Preserve first & last 2 chars, mask middle (e.g. AB****4F)",
  },
  {
    value: "FULL",
    label: "Full",
    description: "Replace entire value with [REDACTED]",
  },
  {
    value: "SYNTHETIC",
    label: "Synthetic",
    description: "Replace with format-matching fake values",
  },
];

const DISABLED_STATUSES: JobStatus[] = ["PENDING", "EXTRACTING", "PII_DETECTING", "REDACTING"];

interface RedactionControlsProps {
  docId: string;
  status: JobStatus;
  redactedUrl?: string | null;
}

export function RedactionControls({ docId, status, redactedUrl }: RedactionControlsProps) {
  const [selectedLevel, setSelectedLevel] = useState<RedactionLevel>("FULL");
  const redactMutation = useRedactMutation(docId);
  const isDisabled = DISABLED_STATUSES.includes(status) || redactMutation.isPending;

  const handleRedact = async () => {
    try {
      await redactMutation.mutateAsync(selectedLevel);
      toast.success("Redaction started. Polling for completion…");
    } catch (err: any) {
      const message = err?.response?.data?.detail ?? "Redaction failed.";
      toast.error(message);
    }
  };

  return (
    <div className="rounded-lg border bg-white p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Shield className="w-4 h-4 text-blue-600" />
        <h3 className="text-sm font-semibold text-gray-700">Apply Redaction</h3>
      </div>

      {/* Redaction level selection */}
      <div className="space-y-2">
        {REDACTION_OPTIONS.map((option) => (
          <label
            key={option.value}
            className={cn(
              "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
              selectedLevel === option.value
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:bg-gray-50",
              isDisabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <input
              type="radio"
              name="redaction_level"
              value={option.value}
              checked={selectedLevel === option.value}
              onChange={() => setSelectedLevel(option.value)}
              disabled={isDisabled}
              className="mt-0.5"
            />
            <div>
              <p className="text-sm font-medium text-gray-800">{option.label}</p>
              <p className="text-xs text-gray-500">{option.description}</p>
            </div>
          </label>
        ))}
      </div>

      {/* Apply button */}
      <button
        onClick={handleRedact}
        disabled={isDisabled}
        className={cn(
          "w-full py-2 px-4 rounded-lg text-sm font-medium transition-colors",
          isDisabled
            ? "bg-gray-100 text-gray-400 cursor-not-allowed"
            : "bg-blue-600 text-white hover:bg-blue-700"
        )}
      >
        {redactMutation.isPending || status === "REDACTING"
          ? "Redacting…"
          : "Apply Redaction"}
      </button>

      {/* Download buttons — shown when completed */}
      {status === "COMPLETED" && redactedUrl && (
        <div className="pt-2 border-t space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Downloads
          </p>
          <button
            onClick={async () => {
              try {
                const res = await fetch(redactedUrl);
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "redacted_document.pdf";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              } catch {
                window.open(redactedUrl, "_blank");
              }
            }}
            className="flex items-center gap-2 w-full py-2 px-3 rounded-lg border border-green-300 bg-green-50 text-green-700 text-sm hover:bg-green-100 transition-colors"
          >
            <Download className="w-4 h-4" />
            Download Redacted Document
          </button>
        </div>
      )}
    </div>
  );
}
