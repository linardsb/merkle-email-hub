"use client";

import { useState } from "react";
import { Paintbrush, ChevronDown, ChevronUp, Loader2, AlertTriangle } from "../icons";
import { useCSSCompile } from "@/hooks/use-css-compile";
import type { CSSConversionSchema } from "@/types/css-compiler";

interface CSSCompilerPanelProps {
  html: string;
  onHtmlUpdate?: (html: string) => void;
}

function formatKB(bytes: number): string {
  return (bytes / 1024).toFixed(1);
}

function ConversionRow({ conv }: { conv: CSSConversionSchema }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded border border-border bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-2.5 py-2 text-left text-xs"
      >
        <div className="flex items-center gap-1 font-mono">
          <span className="text-foreground">
            {conv.original_property}: {conv.original_value}
          </span>
          <span className="text-foreground-muted">→</span>
          <span className="text-status-success">
            {conv.replacement_property}: {conv.replacement_value}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="h-3 w-3 shrink-0 text-foreground-muted" />
        ) : (
          <ChevronDown className="h-3 w-3 shrink-0 text-foreground-muted" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-border px-2.5 py-2 space-y-1">
          <p className="text-[10px] text-foreground-muted">
            {`Reason: ${conv.reason}`}
          </p>
          {conv.affected_clients.length > 0 && (
            <p className="text-[10px] text-foreground-muted">
              {`Affects: ${conv.affected_clients.join(", ")}`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function CSSCompilerPanel({ html, onHtmlUpdate }: CSSCompilerPanelProps) {
  const { trigger, data, isMutating } = useCSSCompile();
  const [showConversions, setShowConversions] = useState(false);

  return (
    <div className="rounded-lg bg-surface-muted p-3">
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Paintbrush className="h-4 w-4 text-foreground-muted" />
          <h3 className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
            {"CSS Compiler"}
          </h3>
        </div>
        <button
          type="button"
          disabled={isMutating}
          onClick={() => trigger({ html })}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          {isMutating ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              {"Compiling…"}
            </>
          ) : (
            "Compile"
          )}
        </button>
      </div>

      {/* Empty state */}
      {!data && !isMutating && (
        <p className="text-xs text-foreground-muted">{"Compile CSS to optimize for email client compatibility."}</p>
      )}

      {data && (
        <div className="space-y-3">
          {/* Size comparison */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground-muted">
                {`Original: ${formatKB(data.original_size)} KB`}
              </span>
              <span className="rounded-full bg-badge-success-bg px-2 py-0.5 text-[10px] font-medium text-badge-success-text">
                {`-${data.reduction_pct.toFixed(1)}%`}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div className="h-full w-full rounded-full bg-foreground-muted/30" />
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground-muted">
                {`Compiled: ${formatKB(data.compiled_size)} KB`}
              </span>
              <span className="text-[10px] text-foreground-muted">
                {`Compiled in ${data.compile_time_ms.toFixed(0)}ms`}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-status-success transition-all"
                style={{
                  width: `${data.original_size > 0 ? (data.compiled_size / data.original_size) * 100 : 100}%`,
                }}
              />
            </div>
          </div>

          {/* Apply button */}
          {onHtmlUpdate && data.reduction_pct > 0 && (
            <button
              type="button"
              onClick={() => onHtmlUpdate(data.html)}
              className="inline-flex items-center gap-1 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              {"Apply Compiled CSS"}
            </button>
          )}

          {/* Warnings */}
          {data.warnings.length > 0 && (
            <div className="rounded border border-status-warning/30 bg-badge-warning-bg p-2">
              <div className="mb-1 flex items-center gap-1.5">
                <AlertTriangle className="h-3 w-3 text-badge-warning-text" />
                <h4 className="text-xs font-medium text-badge-warning-text">
                  {"Warnings"}
                </h4>
              </div>
              <ul className="space-y-0.5">
                {data.warnings.map((w: string, i: number) => (
                  <li key={i} className="text-[10px] text-foreground-muted">
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Removed properties */}
          <div>
            <h4 className="mb-1 text-xs font-medium text-foreground-muted">
              {"Removed Properties"}
            </h4>
            {data.removed_properties.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {data.removed_properties.map((prop: string) => (
                  <span
                    key={prop}
                    className="rounded-full bg-card px-2 py-0.5 font-mono text-[10px] text-foreground-muted"
                  >
                    {prop}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-[10px] text-foreground-muted">
                {"No properties removed"}
              </p>
            )}
          </div>

          {/* Conversions */}
          <div>
            <button
              type="button"
              onClick={() => setShowConversions((v) => !v)}
              className="flex w-full items-center justify-between text-xs font-medium text-foreground-muted"
            >
              <span>
                {"Conversions"} ({data.conversions.length})
              </span>
              {showConversions ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>
            {showConversions && (
              <div className="mt-1.5 space-y-1.5">
                {data.conversions.length > 0 ? (
                  data.conversions.map((conv: CSSConversionSchema, i: number) => (
                    <ConversionRow key={`${conv.original_property}-${i}`} conv={conv} />
                  ))
                ) : (
                  <p className="text-[10px] text-foreground-muted">
                    {"No conversions needed"}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
