"use client";

import { CheckCircle2, XCircle, AlertTriangle } from "../icons";
import type { QACheckResult } from "@/types/qa";

interface QACheckItemProps {
  check: QACheckResult;
  isOverridden?: boolean;
  onHighlightSection?: (sectionId: string) => void;
}

export function QACheckItem({ check, isOverridden, onHighlightSection }: QACheckItemProps) {
  // Extract section_id from check metadata if available (best-effort)
  const sectionId = (check as Record<string, unknown>).section_id as string | undefined;
  const label = check.check_name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const scorePercent = Math.round(check.score * 100);

  return (
    <div
      className={`border-border flex items-start gap-3 rounded-md border px-3 py-2.5${sectionId && onHighlightSection ? "hover:bg-accent/50 cursor-pointer" : ""}`}
      onClick={sectionId && onHighlightSection ? () => onHighlightSection(sectionId) : undefined}
      role={sectionId && onHighlightSection ? "button" : undefined}
      tabIndex={sectionId && onHighlightSection ? 0 : undefined}
    >
      {/* Status icon */}
      <div className="mt-0.5 shrink-0">
        {check.passed ? (
          <CheckCircle2 className="text-status-success h-4 w-4" />
        ) : isOverridden ? (
          <AlertTriangle className="text-status-warning h-4 w-4" />
        ) : (
          <XCircle className="text-destructive h-4 w-4" />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <span className="text-foreground text-sm font-medium">
            {label}
            {isOverridden && (
              <span className="text-status-warning ml-2 text-xs">{"Overridden"}</span>
            )}
          </span>
          <span className="text-muted-foreground text-xs">{scorePercent}%</span>
        </div>

        {/* Score bar */}
        <div className="bg-muted mt-1.5 h-1 w-full rounded-full">
          <div
            className={`h-1 rounded-full transition-all ${
              check.passed
                ? "bg-status-success"
                : isOverridden
                  ? "bg-status-warning"
                  : "bg-destructive"
            }`}
            style={{ width: `${scorePercent}%` }}
          />
        </div>

        {/* Details (only for failures) */}
        {!check.passed && check.details && (
          <p className="text-muted-foreground mt-1.5 text-xs">{check.details}</p>
        )}
      </div>
    </div>
  );
}
