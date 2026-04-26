"use client";

import type { PIIEntity } from "@/types/api";
import { PIIHighlighter } from "./PIIHighlighter";

interface DocumentViewerProps {
  text: string;
  entities: PIIEntity[];
  isLoading?: boolean;
  charCount?: number;
}

export function DocumentViewer({ text, entities, isLoading, charCount }: DocumentViewerProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border bg-white p-4 space-y-2">
        <div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-5/6" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-2/3" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50">
        <span className="text-sm font-medium text-gray-700">Extracted Text</span>
        <div className="flex gap-4 text-xs text-gray-500">
          <span>{(charCount ?? text.length).toLocaleString()} chars</span>
          <span>{entities.length} PII entities</span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 max-h-96 overflow-y-auto">
        {text ? (
          <PIIHighlighter text={text} entities={entities} />
        ) : (
          <p className="text-sm text-gray-400 italic">
            Text will appear here after extraction completes.
          </p>
        )}
      </div>

      {/* Legend */}
      {entities.length > 0 && (
        <div className="px-4 py-2 border-t bg-gray-50 flex flex-wrap gap-2">
          {Array.from(new Set(entities.map((e) => e.entity_type))).map((type) => (
            <span
              key={type}
              className={`text-xs px-2 py-0.5 rounded-full font-medium`}
              style={{ backgroundColor: getEntityColor(type) }}
            >
              {type}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function getEntityColor(type: string): string {
  const colors: Record<string, string> = {
    AADHAAR: "#fecaca",
    PAN: "#fed7aa",
    DRIVING_LICENSE: "#fef08a",
    EMAIL_ADDRESS: "#bfdbfe",
    PHONE_NUMBER: "#e9d5ff",
    PERSON: "#bbf7d0",
  };
  return colors[type] ?? "#e5e7eb";
}
