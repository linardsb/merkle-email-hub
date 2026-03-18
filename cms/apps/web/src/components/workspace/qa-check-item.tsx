"use client";

import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
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
      className={`flex items-start gap-3 rounded-md border border-border px-3 py-2.5${sectionId && onHighlightSection ? " cursor-pointer hover:bg-accent/50" : ""}`}
      onClick={sectionId && onHighlightSection ? () => onHighlightSection(sectionId) : undefined}
      role={sectionId && onHighlightSection ? "button" : undefined}
      tabIndex={sectionId && onHighlightSection ? 0 : undefined}
    >
      {/* Status icon */}
      <div className="mt-0.5 shrink-0">
        {check.passed ? (
          <CheckCircle2 className="h-4 w-4 text-status-success" />
        ) : isOverridden ? (
          <AlertTriangle className="h-4 w-4 text-status-warning" />
        ) : (
          <XCircle className="h-4 w-4 text-destructive" />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-foreground">
            {label}
            {isOverridden && (
              <span className="ml-2 text-xs text-status-warning">
                {"Overridden"}
              </span>
            )}
          </span>
          <span className="text-xs text-muted-foreground">{scorePercent}%</span>
        </div>

        {/* Score bar */}
        <div className="mt-1.5 h-1 w-full rounded-full bg-muted">
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
          <p className="mt-1.5 text-xs text-muted-foreground">
            {check.details}
          </p>
        )}
      </div>
    </div>
  );
}
