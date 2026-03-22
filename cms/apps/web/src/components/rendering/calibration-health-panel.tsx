"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle, RefreshCw } from "lucide-react";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { CLIENT_DISPLAY_NAMES, type ClientProfile } from "@/types/rendering";
import type { CalibrationSummaryResponse } from "@/types/rendering-dashboard";

interface CalibrationHealthPanelProps {
  summary: CalibrationSummaryResponse | undefined;
  isLoading: boolean;
  onRecalibrate: (clientId: string) => void;
  isAdmin: boolean;
}

function SparklineSvg({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const h = 20;
  const w = 60;
  const max = Math.max(...values, 100);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={w} height={h} className="inline-block" aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="text-foreground-accent"
      />
    </svg>
  );
}

export function CalibrationHealthPanel({
  summary,
  isLoading,
  onRecalibrate,
  isAdmin,
}: CalibrationHealthPanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (!isAdmin) return null;

  return (
    <div className="rounded-lg border border-card-border bg-card-bg">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium text-foreground"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-foreground-muted" />
        ) : (
          <ChevronRight className="h-4 w-4 text-foreground-muted" />
        )}
        Calibration Health
      </button>

      {expanded && (
        <div className="border-t border-card-border px-4 py-3">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full rounded" />
              ))}
            </div>
          ) : !summary || summary.items.length === 0 ? (
            <p className="text-sm text-foreground-muted">
              No calibration data available yet.
            </p>
          ) : (
            <div className="space-y-1.5">
              {summary.items.map((item) => {
                const displayName =
                  CLIENT_DISPLAY_NAMES[item.client_id as ClientProfile] ??
                  item.client_id;
                return (
                  <div
                    key={item.client_id}
                    className="flex items-center gap-3 rounded-md border border-card-border px-3 py-2 text-sm"
                  >
                    {/* Client name */}
                    <span className="w-36 shrink-0 font-medium text-foreground">
                      {displayName}
                    </span>

                    {/* Sparkline */}
                    <SparklineSvg values={item.accuracy_trend} />

                    {/* Accuracy */}
                    <span className="w-14 shrink-0 font-mono text-xs text-foreground-muted">
                      {item.current_accuracy.toFixed(0)}%
                    </span>

                    {/* Last calibrated */}
                    <span className="flex-1 text-xs text-foreground-muted">
                      {item.last_calibrated
                        ? new Date(item.last_calibrated).toLocaleDateString()
                        : "Never"}
                    </span>

                    {/* Regression alert */}
                    {item.regression_alert && (
                      <span title="Accuracy regression detected">
                        <AlertTriangle className="h-4 w-4 shrink-0 text-status-warning" />
                      </span>
                    )}

                    {/* Recalibrate button */}
                    <button
                      type="button"
                      onClick={() => onRecalibrate(item.client_id)}
                      className="flex shrink-0 items-center gap-1 rounded border border-card-border px-2 py-1 text-xs text-foreground-muted hover:text-foreground"
                    >
                      <RefreshCw className="h-3 w-3" />
                      Recalibrate
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
