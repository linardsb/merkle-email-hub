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
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? styles.pending}`}
    >
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

export function RenderingTestList({
  tests,
  onScreenshotClick,
  compareIds,
  onCompareToggle,
}: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-6">
      <h2 className="text-foreground text-lg font-semibold">{"Recent Tests"}</h2>

      <div className="mt-4 overflow-x-auto">
        {/* Header */}
        <div
          className={`grid ${GRID_COLS} border-card-border items-center gap-x-2 border-b pb-2 text-sm`}
        >
          <div />
          <div />
          <div className="text-foreground-muted font-medium">{"Status"}</div>
          <div className="text-foreground-muted font-medium">{"Provider"}</div>
          <div className="text-foreground-muted font-medium">{"Completion Rate"}</div>
          <div className="text-foreground-muted font-medium">{"Clients"}</div>
          <div />
          <div className="text-foreground-muted font-medium">{"Date"}</div>
        </div>

        {/* Rows */}
        {tests.map((test) => {
          const isExpanded = expandedId === test.id;
          const isCompareSelected = compareIds[0] === test.id || compareIds[1] === test.id;
          const isProcessing = test.status === "pending" || test.status === "processing";

          return (
            <div key={test.id}>
              <div
                className={`grid w-full ${GRID_COLS} border-card-border/50 items-center gap-x-2 border-b py-3 text-sm`}
              >
                {/* Compare checkbox */}
                <span className="flex justify-center">
                  <input
                    type="checkbox"
                    checked={isCompareSelected}
                    onChange={() => onCompareToggle(test.id)}
                    className="border-card-border rounded"
                    title={"Compare"}
                  />
                </span>
                {/* Expand toggle */}
                <button
                  className="flex justify-center"
                  onClick={() => setExpandedId(isExpanded ? null : test.id)}
                >
                  {isExpanded ? (
                    <ChevronDown className="text-foreground-muted h-4 w-4" />
                  ) : (
                    <ChevronRight className="text-foreground-muted h-4 w-4" />
                  )}
                </button>
                <span className={isProcessing ? "animate-pulse" : ""}>
                  {statusBadge(test.status)}
                </span>
                <span className="text-foreground-muted capitalize">
                  {test.provider === "email_on_acid" ? "Email on Acid" : "Litmus"}
                </span>
                <span className="text-foreground font-medium">{completionRate(test)}%</span>
                <span className="text-foreground-muted">{test.clients_requested}</span>
                <span className="text-foreground-muted truncate text-xs">{`Test #${test.id}`}</span>
                <span className="text-foreground-muted">{formatDate(test.created_at)}</span>
              </div>

              {isExpanded && (
                <div className="border-card-border bg-surface-muted/20 border-b p-4">
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                    {(test.screenshots ?? []).map((screenshot) => (
                      <button
                        key={screenshot.client_name}
                        className="group/thumb border-card-border bg-card-bg relative overflow-hidden rounded-md border transition-shadow hover:shadow-md"
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
                          <div className="bg-surface-muted flex aspect-[3/2] w-full items-center justify-center">
                            <ImageOff className="text-foreground-muted/40 h-6 w-6" />
                          </div>
                        )}
                        <div className="flex items-center justify-between p-2">
                          <span className="text-foreground truncate text-xs">
                            {screenshot.client_name}
                          </span>
                          <span
                            className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${screenshotStatusDot(screenshot.status ?? "")}`}
                          />
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
