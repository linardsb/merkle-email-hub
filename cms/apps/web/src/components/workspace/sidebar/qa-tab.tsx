"use client";

import { useMemo, useState } from "react";
import { ShieldCheck, ShieldAlert, ChevronDown, ChevronUp } from "lucide-react";
import { QACheckItem } from "../qa-check-item";
import { QAOverrideDialog } from "../qa-override-dialog";
import { useSession } from "next-auth/react";
import type { QAResultResponse } from "@/types/qa";

interface QATabProps {
  result: QAResultResponse;
  onOverrideSuccess: () => void;
  onHighlightSection?: (sectionId: string) => void;
}

export function QATab({ result, onOverrideSuccess, onHighlightSection }: QATabProps) {
  const session = useSession();
  const userRole = session.data?.user?.role;
  const canOverride =
    !result.passed &&
    !result.override &&
    (userRole === "admin" || userRole === "developer");

  const [overrideOpen, setOverrideOpen] = useState(false);
  const [showPassing, setShowPassing] = useState(false);

  const scorePercent = Math.round(result.overall_score * 100);
  const checks = result.checks ?? [];
  const failedChecks = useMemo(() => checks.filter((c) => !c.passed), [checks]);
  const passedChecks = useMemo(() => checks.filter((c) => c.passed), [checks]);
  const overriddenNames = useMemo(
    () => new Set(result.override?.checks_overridden ?? []),
    [result.override?.checks_overridden]
  );

  return (
    <div className="flex h-full flex-col">
      {/* Score summary */}
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          {result.passed || result.override ? (
            <ShieldCheck className="h-5 w-5 text-status-success" />
          ) : (
            <ShieldAlert className="h-5 w-5 text-destructive" />
          )}
          <span className="text-2xl font-bold text-foreground">
            {scorePercent}%
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              result.passed || result.override
                ? "bg-badge-success-bg text-badge-success-text"
                : "bg-badge-danger-bg text-badge-danger-text"
            }`}
          >
            {result.passed
              ? "Passed"
              : result.override
                ? "Overridden"
                : "Failed"}
          </span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {`${result.checks_passed} of ${result.checks_total} checks passed`}
        </p>

        {result.override && (
          <div className="mt-2 rounded border border-status-warning/30 bg-badge-warning-bg px-2.5 py-2 text-xs text-muted-foreground">
            <p className="font-medium text-badge-warning-text">
              {"Override applied"}
            </p>
            <p className="mt-0.5">{result.override.justification}</p>
          </div>
        )}
      </div>

      {/* Checks list */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {failedChecks.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-medium uppercase tracking-wider text-destructive">
              {`${failedChecks.length} Failed`}
            </h3>
            {failedChecks.map((check) => (
              <QACheckItem
                key={check.check_name}
                check={check}
                isOverridden={overriddenNames.has(check.check_name)}
                onHighlightSection={onHighlightSection}
              />
            ))}
          </div>
        )}

        {passedChecks.length > 0 && (
          <div className={failedChecks.length > 0 ? "mt-4" : ""}>
            <button
              type="button"
              onClick={() => setShowPassing((v) => !v)}
              className="flex w-full items-center justify-between text-xs font-medium uppercase tracking-wider text-status-success"
            >
              {`${passedChecks.length} Passed`}
              {showPassing ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>
            {showPassing && (
              <div className="mt-2 space-y-2">
                {passedChecks.map((check) => (
                  <QACheckItem
                    key={check.check_name}
                    check={check}
                    onHighlightSection={onHighlightSection}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Override button */}
      {canOverride && (
        <div className="border-t border-border px-4 py-3">
          <button
            type="button"
            onClick={() => setOverrideOpen(true)}
            className="w-full rounded-md border border-status-warning bg-badge-warning-bg px-3 py-2 text-sm font-medium text-badge-warning-text transition-colors hover:opacity-80"
          >
            {"Override Failing Checks"}
          </button>
        </div>
      )}

      <QAOverrideDialog
        open={overrideOpen}
        onOpenChange={setOverrideOpen}
        resultId={result.id}
        failedChecks={failedChecks}
        onSuccess={() => {
          setOverrideOpen(false);
          onOverrideSuccess();
        }}
      />
    </div>
  );
}
