"use client";

import { useCallback, useRef } from "react";
import { Loader2, ShieldCheck, ShieldAlert, SkipForward } from "lucide-react";
import { useSession } from "next-auth/react";
import { useGateEvaluate } from "@/hooks/use-rendering-gate";
import { GateSummaryBadge } from "./gate-summary-badge";
import { GateClientRow } from "./gate-client-row";

interface GatePanelProps {
  /** HTML to evaluate. Panel auto-triggers when html changes and is non-null. */
  html: string | null;
  /** Project ID for loading project-specific thresholds. */
  projectId: number;
  /** Target clients to evaluate (optional — backend defaults to project targets). */
  targetClients?: string[];
  /** Called when user explicitly approves (either gate passed or admin override). */
  onApproved: () => void;
  /** Called when user cancels. */
  onCancel: () => void;
  /** Label for the approve button (e.g. "Export", "Push to ESP"). */
  approveLabel?: string;
}

export function GatePanel({
  html,
  projectId,
  targetClients,
  onApproved,
  onCancel,
  approveLabel = "Continue",
}: GatePanelProps) {
  const session = useSession();
  const isAdmin = session.data?.user?.role === "admin";

  const { data: gateResult, trigger, isMutating, error } = useGateEvaluate();

  const runEvaluation = useCallback(() => {
    if (!html) return;
    trigger({
      html,
      project_id: projectId,
      target_clients: targetClients,
    });
  }, [html, projectId, targetClients, trigger]);

  // Auto-trigger on mount if html is ready and no result yet.
  // Ref guard prevents re-triggering across renders before isMutating flips.
  const triggeredRef = useRef(false);
  const needsEvaluation = html && !gateResult && !isMutating && !error;

  if (needsEvaluation && !triggeredRef.current) {
    triggeredRef.current = true;
    runEvaluation();
  }

  // -- Loading --
  if (isMutating) {
    return (
      <div className="flex flex-col items-center gap-3 py-6">
        <Loader2 className="h-6 w-6 animate-spin text-foreground-muted" />
        <p className="text-sm text-foreground-muted">Evaluating rendering confidence...</p>
      </div>
    );
  }

  // -- Error --
  if (error) {
    return (
      <div className="space-y-3">
        <div className="rounded-md bg-status-danger/10 p-3 text-sm text-status-danger">
          Gate evaluation failed: {error.message}
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground hover:bg-surface-hover"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={runEvaluation}
            className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse hover:bg-interactive-hover"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // -- No result yet (waiting for auto-trigger) --
  if (!gateResult) {
    return null;
  }

  // -- Results --
  const canProceed = gateResult.passed || gateResult.verdict === "warn";
  const isBlocked = gateResult.verdict === "block";

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isBlocked ? (
            <ShieldAlert className="h-5 w-5 text-status-danger" />
          ) : (
            <ShieldCheck className="h-5 w-5 text-status-success" />
          )}
          <span className="text-sm font-medium text-foreground">Rendering Gate</span>
        </div>
        <GateSummaryBadge
          verdict={gateResult.verdict}
          blockingCount={gateResult.blocking_clients.length}
        />
      </div>

      {/* Client results list */}
      <div className="space-y-1.5">
        {gateResult.client_results.map((cr) => (
          <GateClientRow key={cr.client_name} result={cr} />
        ))}
      </div>

      {/* Global recommendations */}
      {gateResult.recommendations.length > 0 && (
        <div className="rounded-md bg-status-warning/10 p-3 text-xs text-foreground-muted">
          <p className="mb-1 font-medium text-foreground">Recommendations</p>
          <ul className="list-inside list-disc space-y-0.5">
            {gateResult.recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 border-t border-card-border pt-3">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground hover:bg-surface-hover"
        >
          Cancel
        </button>

        {/* Admin override when blocked */}
        {isBlocked && isAdmin && (
          <button
            type="button"
            onClick={onApproved}
            className="flex items-center gap-1.5 rounded-md border border-status-warning px-3 py-1.5 text-sm font-medium text-status-warning hover:bg-status-warning/10"
          >
            <SkipForward className="h-4 w-4" />
            Override & Send Anyway
          </button>
        )}

        {/* Normal proceed when allowed */}
        {canProceed && (
          <button
            type="button"
            onClick={onApproved}
            className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse hover:bg-interactive-hover"
          >
            {approveLabel}
          </button>
        )}

        {/* Blocked non-admin — no proceed button, only cancel */}
        {isBlocked && !isAdmin && (
          <p className="text-xs text-foreground-muted">
            Blocked — ask an admin to override or fix the issues above.
          </p>
        )}
      </div>
    </div>
  );
}
