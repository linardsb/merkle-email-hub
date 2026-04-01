"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, ImageOff } from "../icons";
import type { RenderingTest, ScreenshotResult } from "@/types/rendering";

interface Props {
  tests: RenderingTest[];
  onScreenshotClick: (result: ScreenshotResult) => void;
  compareIds: [number | null, number | null];
  onCompareToggle: (testId: number) => void;
}

function statusBadge(status: string) {
  const styles: Record<string, string> = {
    complete: "bg-badge-success-bg text-badge-success-text",
    failed: "bg-badge-danger-bg text-badge-danger-text",
    processing: "bg-badge-warning-bg text-badge-warning-text",
    pending: "bg-badge-neutral-bg text-badge-neutral-text",
  };
  const labels: Record<string, string> = {
    complete: "Complete",
    failed: "Failed",
    processing: "Processing",
    pending: "Pending",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? styles.pending}`}>
      {labels[status] ?? status}
    </span>
  );
}

function screenshotStatusDot(status: string) {
  const styles: Record<string, string> = {
    complete: "bg-status-success",
    failed: "bg-status-danger",
    pending: "bg-surface-muted",
  };
  return styles[status] ?? styles.pending;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function completionRate(test: RenderingTest): number {
  if (test.clients_requested === 0) return 0;
  return Math.round(((test.clients_completed ?? 0) / test.clients_requested) * 100);
}

const GRID_COLS = "grid-cols-[2rem_2rem_6rem_1fr_7rem_5.5rem_3rem_9rem]";

export function RenderingTestList({ tests, onScreenshotClick, compareIds, onCompareToggle }: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <h2 className="text-lg font-semibold text-foreground">{"Recent Tests"}</h2>

      <div className="mt-4 overflow-x-auto">
        {/* Header */}
        <div className={`grid ${GRID_COLS} items-center gap-x-2 border-b border-card-border pb-2 text-sm`}>
          <div />
          <div />
          <div className="font-medium text-foreground-muted">{"Status"}</div>
          <div className="font-medium text-foreground-muted">{"Provider"}</div>
          <div className="font-medium text-foreground-muted">{"Completion Rate"}</div>
          <div className="font-medium text-foreground-muted">{"Clients"}</div>
          <div />
          <div className="font-medium text-foreground-muted">{"Date"}</div>
        </div>

        {/* Rows */}
        {tests.map((test) => {
          const isExpanded = expandedId === test.id;
          const isCompareSelected = compareIds[0] === test.id || compareIds[1] === test.id;
          const isProcessing = test.status === "pending" || test.status === "processing";

          return (
            <div key={test.id}>
              <div className={`grid w-full ${GRID_COLS} items-center gap-x-2 border-b border-card-border/50 py-3 text-sm`}>
                {/* Compare checkbox */}
                <span className="flex justify-center">
                  <input
                    type="checkbox"
                    checked={isCompareSelected}
                    onChange={() => onCompareToggle(test.id)}
                    className="rounded border-card-border"
                    title={"Compare"}
                  />
                </span>
                {/* Expand toggle */}
                <button
                  className="flex justify-center"
                  onClick={() => setExpandedId(isExpanded ? null : test.id)}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-foreground-muted" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-foreground-muted" />
                  )}
                </button>
                <span className={isProcessing ? "animate-pulse" : ""}>{statusBadge(test.status)}</span>
                <span className="capitalize text-foreground-muted">
                  {test.provider === "email_on_acid" ? "Email on Acid" : "Litmus"}
                </span>
                <span className="font-medium text-foreground">{completionRate(test)}%</span>
                <span className="text-foreground-muted">{test.clients_requested}</span>
                <span className="truncate text-xs text-foreground-muted">
                  {`Test #${test.id}`}
                </span>
                <span className="text-foreground-muted">{formatDate(test.created_at)}</span>
              </div>

              {isExpanded && (
                <div className="border-b border-card-border bg-surface-muted/20 p-4">
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                    {(test.screenshots ?? []).map((screenshot) => (
                      <button
                        key={screenshot.client_name}
                        className="group/thumb relative overflow-hidden rounded-md border border-card-border bg-card-bg transition-shadow hover:shadow-md"
                        onClick={() => onScreenshotClick(screenshot)}
                      >
                        {screenshot.screenshot_url ? (
                          <img
                            src={screenshot.screenshot_url}
                            alt={screenshot.client_name}
                            className="aspect-[3/2] w-full object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <div className="flex aspect-[3/2] w-full items-center justify-center bg-surface-muted">
                            <ImageOff className="h-6 w-6 text-foreground-muted/40" />
                          </div>
                        )}
                        <div className="flex items-center justify-between p-2">
                          <span className="truncate text-xs text-foreground">
                            {screenshot.client_name}
                          </span>
                          <span className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${screenshotStatusDot(screenshot.status ?? "")}`} />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
