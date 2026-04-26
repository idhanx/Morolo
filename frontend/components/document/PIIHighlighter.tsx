"use client";

import type { PIIEntity } from "@/types/api";
import { PII_ENTITY_COLORS } from "@/types/api";
import { cn } from "@/lib/utils";

interface Segment {
  text: string;
  entity?: PIIEntity;
}

function buildSegments(text: string, entities: PIIEntity[]): Segment[] {
  if (!entities.length) return [{ text }];

  // Sort by start offset
  const sorted = [...entities].sort((a, b) => a.start_offset - b.start_offset);
  const segments: Segment[] = [];
  let cursor = 0;

  for (const entity of sorted) {
    if (entity.start_offset > cursor) {
      segments.push({ text: text.slice(cursor, entity.start_offset) });
    }
    segments.push({
      text: text.slice(entity.start_offset, entity.end_offset),
      entity,
    });
    cursor = entity.end_offset;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor) });
  }

  return segments;
}

interface PIIHighlighterProps {
  text: string;
  entities: PIIEntity[];
}

export function PIIHighlighter({ text, entities }: PIIHighlighterProps) {
  const segments = buildSegments(text, entities);

  return (
    <div className="font-mono text-sm leading-relaxed whitespace-pre-wrap break-words">
      {segments.map((seg, i) =>
        seg.entity ? (
          <span
            key={i}
            title={`${seg.entity.entity_type} (${(seg.entity.confidence * 100).toFixed(0)}% confidence${seg.entity.subtype ? ` · ${seg.entity.subtype}` : ""})`}
            className={cn(
              "rounded px-0.5 cursor-help",
              PII_ENTITY_COLORS[seg.entity.entity_type] ?? "bg-gray-200"
            )}
          >
            {seg.text}
          </span>
        ) : (
          <span key={i}>{seg.text}</span>
        )
      )}
    </div>
  );
}
