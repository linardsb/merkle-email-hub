"use client";

import { useMemo } from "react";
import type { SchemaInjectResponse } from "@/types/gmail-intelligence";

interface SchemaPreviewProps {
  result: SchemaInjectResponse;
  onApply?: (html: string) => void;
}

function extractJsonLd(html: string): string | null {
  const match = html.match(
    /<script\s+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/i,
  );
  if (!match?.[1]) return null;
  try {
    return JSON.stringify(JSON.parse(match[1]), null, 2);
  } catch {
    return match[1].trim();
  }
}

export function SchemaPreview({ result, onApply }: SchemaPreviewProps) {
  const jsonLd = useMemo(() => extractJsonLd(result.html), [result.html]);

  return (
    <div className="space-y-2.5">
      {/* Injected badge */}
      <span
        className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${
          result.injected
            ? "bg-badge-success-bg text-badge-success-text"
            : "bg-surface-muted text-foreground-muted"
        }`}
      >
        {result.injected ? "Markup injected" : "No applicable markup detected"}
      </span>

      {/* Detected intent */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-foreground-muted">{"Detected Intent"}:</span>
        <span className="font-medium text-foreground">
          {result.intent.intent_type}
        </span>
        <div className="flex-1">
          <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-accent-primary transition-all"
              style={{ width: `${result.intent.confidence * 100}%` }}
            />
          </div>
        </div>
        <span className="text-[10px] text-foreground-muted">
          {Math.round(result.intent.confidence * 100)}%
        </span>
      </div>

      {/* Entities */}
      {result.entities.length > 0 && (
        <div>
          <h4 className="mb-1 text-[10px] font-medium text-foreground-muted">
            {"Extracted Entities"}
          </h4>
          <div className="flex flex-wrap gap-1">
            {result.entities.map((entity, i) => (
              <span
                key={i}
                className="rounded-full bg-card px-2 py-0.5 text-[10px] text-foreground-muted"
              >
                {entity.entity_type}: {entity.value}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Schema types */}
      {result.schema_types.length > 0 && (
        <div>
          <h4 className="mb-1 text-[10px] font-medium text-foreground-muted">
            {"Schema Types"}
          </h4>
          <div className="flex flex-wrap gap-1">
            {result.schema_types.map((type) => (
              <span
                key={type}
                className="rounded bg-badge-info-bg px-1.5 py-0.5 text-[10px] font-medium text-badge-info-text"
              >
                {type}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* JSON-LD preview */}
      {jsonLd && (
        <pre className="max-h-48 overflow-auto rounded-lg bg-surface-muted p-3 text-xs text-foreground-muted">
          {jsonLd}
        </pre>
      )}

      {/* Validation errors */}
      {result.validation_errors.length > 0 && (
        <div>
          <h4 className="mb-1 text-[10px] font-medium text-foreground-muted">
            {"Validation Errors"}
          </h4>
          {result.validation_errors.map((err, i) => (
            <span
              key={i}
              className="mr-1 inline-block rounded-full bg-badge-danger-bg px-2 py-0.5 text-[10px] text-badge-danger-text"
            >
              {err}
            </span>
          ))}
        </div>
      )}

      {/* Processing time */}
      <p className="text-[10px] text-foreground-muted">
        {`Processed in ${result.inject_time_ms.toFixed(0)}ms`}
      </p>

      {/* Apply button */}
      {result.injected && onApply && (
        <button
          type="button"
          onClick={() => onApply(result.html)}
          className="inline-flex items-center gap-1 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          {"Apply HTML"}
        </button>
      )}
    </div>
  );
}
