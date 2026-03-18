"use client";

import { useRef, useEffect } from "react";
import { X, Loader2, AlertTriangle, CheckCircle, ImageOff } from "lucide-react";
import { useRenderingComparison } from "@/hooks/use-renderings";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  baselineTestId: number | null;
  currentTestId: number | null;
}

function diffBadge(pct: number) {
  if (pct < 2) return { label: "< 2% diff", className: "bg-badge-success-bg text-badge-success-text" };
  if (pct < 5) return { label: "2-5% diff", className: "bg-badge-warning-bg text-badge-warning-text" };
  return { label: "> 5% diff", className: "bg-badge-danger-bg text-badge-danger-text" };
}

export function VisualRegressionDialog({ open, onOpenChange, baselineTestId, currentTestId }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const { trigger, data, isMutating, error } = useRenderingComparison();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      if (baselineTestId && currentTestId) {
        trigger({ baseline_test_id: baselineTestId, current_test_id: currentTestId });
      }
    }
    if (!open && dialog.open) dialog.close();
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <dialog
      ref={ref}
      className="w-full max-w-[56rem] rounded-lg border border-card-border bg-card-bg p-0 shadow-xl backdrop:bg-black/50"
      onClose={() => onOpenChange(false)}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-card-border p-4">
        <h2 className="text-lg font-semibold text-foreground">
          {"Visual Regression"}: #{baselineTestId} vs #{currentTestId}
        </h2>
        <button
          onClick={() => onOpenChange(false)}
          className="rounded p-1 text-foreground-muted hover:bg-surface-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="p-4">
        {isMutating && (
          <div className="flex flex-col items-center gap-4 py-12">
            <Loader2 className="h-8 w-8 animate-spin text-foreground-accent" />
            <p className="text-sm text-foreground-muted">{"Processing"}</p>
          </div>
        )}

        {error && !isMutating && (
          <div className="flex flex-col items-center gap-4 py-12">
            <AlertTriangle className="h-8 w-8 text-status-danger" />
            <p className="text-sm text-foreground">{"Failed to load rendering data"}</p>
          </div>
        )}

        {data && !isMutating && (
          <>
            {/* Summary */}
            <div className="mb-4 flex items-center gap-3 rounded-lg border border-card-border bg-surface-muted/30 p-3">
              {data.regressions_found > 0 ? (
                <AlertTriangle className="h-5 w-5 text-status-warning" />
              ) : (
                <CheckCircle className="h-5 w-5 text-status-success" />
              )}
              <span className="text-sm text-foreground">
                {data.regressions_found > 0
                  ? `\${data.regressions_found} regressions found across \${data.total_clients} clients`
                  : "No regressions detected"}
              </span>
            </div>

            {/* Diff grid */}
            <div className="space-y-4">
              {(data.diffs ?? []).map((diff) => {
                const badge = diffBadge(diff.diff_percentage);
                return (
                  <div key={diff.client_name} className="rounded-lg border border-card-border p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm font-medium text-foreground">{diff.client_name}</span>
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}>
                          {diff.diff_percentage.toFixed(1)}% — {badge.label}
                        </span>
                        {diff.has_regression && (
                          <span className="rounded-full bg-badge-danger-bg px-2 py-0.5 text-xs font-medium text-badge-danger-text">
                            {"Regression"}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="mb-1 text-xs text-foreground-muted">{"Baseline"}</p>
                        {diff.baseline_url ? (
                          <img
                            src={diff.baseline_url}
                            alt={`${diff.client_name} baseline`}
                            className="w-full rounded border border-card-border object-contain"
                            loading="lazy"
                          />
                        ) : (
                          <div className="flex aspect-[3/2] items-center justify-center rounded border border-card-border bg-surface-muted">
                            <ImageOff className="h-6 w-6 text-foreground-muted/40" />
                          </div>
                        )}
                      </div>
                      <div>
                        <p className="mb-1 text-xs text-foreground-muted">{"Current"}</p>
                        {diff.current_url ? (
                          <img
                            src={diff.current_url}
                            alt={`${diff.client_name} current`}
                            className="w-full rounded border border-card-border object-contain"
                            loading="lazy"
                          />
                        ) : (
                          <div className="flex aspect-[3/2] items-center justify-center rounded border border-card-border bg-surface-muted">
                            <ImageOff className="h-6 w-6 text-foreground-muted/40" />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Close */}
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => onOpenChange(false)}
                className="rounded px-4 py-2 text-sm font-medium text-foreground-muted hover:text-foreground"
              >
                {"Close"}
              </button>
            </div>
          </>
        )}
      </div>
    </dialog>
  );
}
