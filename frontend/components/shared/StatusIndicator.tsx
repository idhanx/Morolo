"use client";

import { Check, X, Loader2 } from "lucide-react";
import type { JobStatus } from "@/types/api";
import { cn } from "@/lib/utils";

const STEPS: { label: string; status: JobStatus }[] = [
  { label: "Upload", status: "PENDING" },
  { label: "Extract", status: "EXTRACTING" },
  { label: "Detect PII", status: "PII_DETECTING" },
  { label: "Redact", status: "REDACTING" },
  { label: "Complete", status: "COMPLETED" },
];

function getStepIndex(status: JobStatus): number {
  const map: Record<JobStatus, number> = {
    PENDING: 0,
    EXTRACTING: 1,
    PII_DETECTING: 2,
    PII_DETECTED: 2,
    REDACTING: 3,
    COMPLETED: 5,  // beyond last step index so all steps show as completed
    FAILED: -1,
  };
  return map[status] ?? 0;
}

interface StatusIndicatorProps {
  status: JobStatus;
  error?: string | null;
}

export function StatusIndicator({ status, error }: StatusIndicatorProps) {
  const currentStep = getStepIndex(status);
  const isFailed = status === "FAILED";

  return (
    <div className="w-full">
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const isCompleted = !isFailed && index < currentStep;
          const isActive = !isFailed && index === currentStep;
          const isFuture = !isFailed && index > currentStep;

          return (
            <div key={step.label} className="flex items-center flex-1">
              {/* Step circle */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors",
                    isCompleted && "bg-green-500 text-white",
                    isActive && "bg-blue-500 text-white",
                    isFuture && "bg-gray-200 text-gray-500",
                    isFailed && "bg-red-500 text-white"
                  )}
                >
                  {isFailed ? (
                    <X className="w-4 h-4" />
                  ) : isCompleted ? (
                    <Check className="w-4 h-4" />
                  ) : isActive ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs mt-1 whitespace-nowrap",
                    isCompleted && "text-green-600",
                    isActive && "text-blue-600 font-medium",
                    isFuture && "text-gray-400",
                    isFailed && "text-red-600"
                  )}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector line */}
              {index < STEPS.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-0.5 mx-2 mt-[-16px]",
                    index < currentStep && !isFailed
                      ? "bg-green-400"
                      : "bg-gray-200"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {isFailed && error && (
        <p className="mt-3 text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
          Error: {error}
        </p>
      )}
    </div>
  );
}
