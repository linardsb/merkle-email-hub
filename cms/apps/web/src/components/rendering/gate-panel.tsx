"use client";

import { useCallback, useRef } from "react";
import { Loader2, ShieldCheck, ShieldAlert, SkipForward } from "../icons";
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
        <Loader2 className="text-foreground-muted h-6 w-6 animate-spin" />
        <p className="text-foreground-muted text-sm">Evaluating rendering confidence...</p>
      </div>
    );
  }

  // -- Error --
  if (error) {
    return (
      <div className="space-y-3">
        <div className="bg-status-danger/10 text-status-danger rounded-md p-3 text-sm">
          Gate evaluation failed: {error.message}
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={runEvaluation}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium"
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
            <ShieldAlert className="text-status-danger h-5 w-5" />
          ) : (
            <ShieldCheck className="text-status-success h-5 w-5" />
          )}
          <span className="text-foreground text-sm font-medium">Rendering Gate</span>
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
        <div className="bg-status-warning/10 text-foreground-muted rounded-md p-3 text-xs">
          <p className="text-foreground mb-1 font-medium">Recommendations</p>
          <ul className="list-inside list-disc space-y-0.5">
            {gateResult.recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="border-card-border flex items-center justify-end gap-2 border-t pt-3">
        <button
          type="button"
          onClick={onCancel}
          className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm"
        >
          Cancel
        </button>

        {/* Admin override when blocked */}
        {isBlocked && isAdmin && (
          <button
            type="button"
            onClick={onApproved}
            className="border-status-warning text-status-warning hover:bg-status-warning/10 flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium"
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
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium"
          >
            {approveLabel}
          </button>
        )}

        {/* Blocked non-admin — no proceed button, only cancel */}
        {isBlocked && !isAdmin && (
          <p className="text-foreground-muted text-xs">
            Blocked — ask an admin to override or fix the issues above.
          </p>
        )}
      </div>
    </div>
  );
}
