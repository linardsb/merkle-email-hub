"use client";

import { useEffect, useCallback } from "react";
import { X, AlertTriangle } from "../icons";
import type { FailurePatternResponse } from "@/types/failure-patterns";

interface FailurePatternDetailDialogProps {
  pattern: FailurePatternResponse;
  onClose: () => void;
}

export function FailurePatternDetailDialog({ pattern, onClose }: FailurePatternDetailDialogProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={"Pattern Detail"}
    >
      <div className="fixed inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div className="border-card-border bg-card-bg relative z-10 w-full max-w-[32rem] rounded-lg border p-6 shadow-lg">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="text-status-warning h-5 w-5" />
            <h2 className="text-foreground text-lg font-semibold">{"Pattern Detail"}</h2>
          </div>
          <button onClick={onClose} className="text-foreground-muted hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-foreground-muted text-xs font-medium">{"Agent"}</p>
              <p className="text-foreground mt-1 text-sm">
                {pattern.agent_name.replace(/_/g, " ")}
              </p>
            </div>
            <div>
              <p className="text-foreground-muted text-xs font-medium">{"QA Check"}</p>
              <p className="text-foreground mt-1 text-sm">{pattern.qa_check.replace(/_/g, " ")}</p>
            </div>
            <div>
              <p className="text-foreground-muted text-xs font-medium">{"Blueprint"}</p>
              <p className="text-foreground mt-1 text-sm">{pattern.blueprint_name || "-"}</p>
            </div>
            <div>
              <p className="text-foreground-muted text-xs font-medium">{"Confidence"}</p>
              <p className="text-foreground mt-1 text-sm">
                {pattern.confidence != null ? `${Math.round(pattern.confidence * 100)}%` : "-"}
              </p>
            </div>
          </div>

          {/* Affected Clients */}
          {pattern.client_ids.length > 0 && (
            <div>
              <p className="text-foreground-muted text-xs font-medium">{"Affected Clients"}</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {pattern.client_ids.map((c) => (
                  <span
                    key={c}
                    className="bg-surface-muted text-foreground rounded px-2 py-0.5 text-xs"
                  >
                    {c.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          <div>
            <p className="text-foreground-muted text-xs font-medium">{"Description"}</p>
            <p className="text-foreground mt-1 text-sm whitespace-pre-wrap">
              {pattern.description}
            </p>
          </div>

          {/* Workaround */}
          {pattern.workaround && (
            <div>
              <p className="text-foreground-muted text-xs font-medium">{"Workaround"}</p>
              <p className="bg-surface-muted text-foreground mt-1 rounded p-3 text-sm">
                {pattern.workaround}
              </p>
            </div>
          )}

          {/* Metadata */}
          <div className="border-card-border border-t pt-4">
            <div className="text-foreground-muted grid grid-cols-2 gap-4 text-xs">
              <div>
                <p className="font-medium">{"First Seen"}</p>
                <p>{new Date(pattern.first_seen).toLocaleString()}</p>
              </div>
              <div>
                <p className="font-medium">{"Last Seen"}</p>
                <p>{new Date(pattern.last_seen).toLocaleString()}</p>
              </div>
              {pattern.run_id && (
                <div className="col-span-2">
                  <p className="font-medium">{"Run ID"}</p>
                  <p className="font-mono">{pattern.run_id}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
