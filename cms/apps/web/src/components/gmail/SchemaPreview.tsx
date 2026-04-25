"use client";

import { useMemo } from "react";
import type { SchemaInjectResponse } from "@/types/gmail-intelligence";

interface SchemaPreviewProps {
  result: SchemaInjectResponse;
  onApply?: (html: string) => void;
}

function extractJsonLd(html: string): string | null {
  const match = html.match(/<script\s+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/i);
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
        <span className="text-foreground font-medium">{result.intent.intent_type}</span>
        <div className="flex-1">
          <div className="bg-muted h-1 w-full overflow-hidden rounded-full">
            <div
              className="bg-accent-primary h-full rounded-full transition-all"
              style={{ width: `${result.intent.confidence * 100}%` }}
            />
          </div>
        </div>
        <span className="text-foreground-muted text-[10px]">
          {Math.round(result.intent.confidence * 100)}%
        </span>
      </div>

      {/* Entities */}
      {result.entities.length > 0 && (
        <div>
          <h4 className="text-foreground-muted mb-1 text-[10px] font-medium">
            {"Extracted Entities"}
          </h4>
          <div className="flex flex-wrap gap-1">
            {result.entities.map((entity, i) => (
              <span
                key={i}
                className="bg-card text-foreground-muted rounded-full px-2 py-0.5 text-[10px]"
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
          <h4 className="text-foreground-muted mb-1 text-[10px] font-medium">{"Schema Types"}</h4>
          <div className="flex flex-wrap gap-1">
            {result.schema_types.map((type) => (
              <span
                key={type}
                className="bg-badge-info-bg text-badge-info-text rounded px-1.5 py-0.5 text-[10px] font-medium"
              >
                {type}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* JSON-LD preview */}
      {jsonLd && (
        <pre className="bg-surface-muted text-foreground-muted max-h-48 overflow-auto rounded-lg p-3 text-xs">
          {jsonLd}
        </pre>
      )}

      {/* Validation errors */}
      {result.validation_errors.length > 0 && (
        <div>
          <h4 className="text-foreground-muted mb-1 text-[10px] font-medium">
            {"Validation Errors"}
          </h4>
          {result.validation_errors.map((err, i) => (
            <span
              key={i}
              className="bg-badge-danger-bg text-badge-danger-text mr-1 inline-block rounded-full px-2 py-0.5 text-[10px]"
            >
              {err}
            </span>
          ))}
        </div>
      )}

      {/* Processing time */}
      <p className="text-foreground-muted text-[10px]">
        {`Processed in ${result.inject_time_ms.toFixed(0)}ms`}
      </p>

      {/* Apply button */}
      {result.injected && onApply && (
        <button
          type="button"
          onClick={() => onApply(result.html)}
          className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
        >
          {"Apply HTML"}
        </button>
      )}
    </div>
  );
}
