"use client";

import type { AuditLogResponse } from "@/types/api";
import { Upload, Search, Shield, Database, AlertCircle } from "lucide-react";

const ACTION_ICONS: Record<string, React.ReactNode> = {
  UPLOAD: <Upload className="w-3.5 h-3.5" />,
  DETECT_PII: <Search className="w-3.5 h-3.5" />,
  REDACT: <Shield className="w-3.5 h-3.5" />,
  INGEST_TO_OM: <Database className="w-3.5 h-3.5" />,
  FAILED: <AlertCircle className="w-3.5 h-3.5 text-red-500" />,
};

interface ActivityTimelineProps {
  logs: AuditLogResponse[];
  isLoading?: boolean;
}

export function ActivityTimeline({ logs, isLoading }: ActivityTimelineProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (!logs.length) {
    return <p className="text-xs text-gray-400 italic">No activity yet.</p>;
  }

  return (
    <div className="space-y-2">
      {logs.map((log) => (
        <div key={log.id} className="flex items-start gap-2 text-xs">
          <div className="mt-0.5 text-gray-500">
            {ACTION_ICONS[log.action] ?? <Database className="w-3.5 h-3.5" />}
          </div>
          <div className="flex-1 min-w-0">
            <span className="font-medium text-gray-700">{log.action}</span>
            <span className="text-gray-400 ml-1">by {log.actor}</span>
          </div>
          <time className="text-gray-400 whitespace-nowrap" title={new Date(log.timestamp + "Z").toLocaleString()}>
            {new Date(log.timestamp + "Z").toLocaleTimeString(undefined, {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </time>
        </div>
      ))}
    </div>
  );
}
