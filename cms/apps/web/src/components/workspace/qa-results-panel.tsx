"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useSession } from "next-auth/react";
import {
  X,
  ShieldCheck,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { QACheckItem } from "./qa-check-item";
import { QAOverrideDialog } from "./qa-override-dialog";
import { VisualQAPanelTab } from "@/components/visual-qa/visual-qa-panel-tab";
import { ChaosTestPanel } from "@/components/qa/ChaosTestPanel";
import { PropertyTestPanel } from "@/components/qa/PropertyTestPanel";
import { OutlookAdvisorPanel } from "@/components/outlook/OutlookAdvisorPanel";
import { CSSCompilerPanel } from "@/components/email-engine/CSSCompilerPanel";
import { GmailPredictionPanel } from "@/components/gmail/GmailPredictionPanel";
import type { QAResultResponse } from "@/types/qa";
import type { VisualQAEntityType } from "@/types/rendering";

interface QAResultsPanelProps {
  result: QAResultResponse;
  onClose: () => void;
  onOverrideSuccess: () => void;
  html?: string;
  entityType?: VisualQAEntityType;
  entityId?: number;
  onHtmlUpdate?: (html: string) => void;
}

export function QAResultsPanel({
  result,
  onClose,
  onOverrideSuccess,
  html,
  entityType,
  entityId,
  onHtmlUpdate,
}: QAResultsPanelProps) {
  const t = useTranslations("qa");
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
  const failedChecks = useMemo(
    () => checks.filter((c) => !c.passed),
    [checks]
  );
  const passedChecks = useMemo(
    () => checks.filter((c) => c.passed),
    [checks]
  );
  const overriddenNames = useMemo(
    () => new Set(result.override?.checks_overridden ?? []),
    [result.override?.checks_overridden]
  );

  return (
    <div className="flex h-full w-80 flex-col border-l border-border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          {result.passed || result.override ? (
            <ShieldCheck className="h-5 w-5 text-status-success" />
          ) : (
            <ShieldAlert className="h-5 w-5 text-destructive" />
          )}
          <h2 className="text-sm font-semibold text-foreground">
            {t("title")}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("close")}
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Score summary */}
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-baseline justify-between">
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
              ? t("statusPassed")
              : result.override
                ? t("statusOverridden")
                : t("statusFailed")}
          </span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {t("checksSummary", {
            passed: result.checks_passed,
            total: result.checks_total,
          })}
        </p>

        {/* Override info */}
        {result.override && (
          <div className="mt-2 rounded border border-status-warning/30 bg-badge-warning-bg px-2.5 py-2 text-xs text-muted-foreground">
            <p className="font-medium text-badge-warning-text">
              {t("overrideApplied")}
            </p>
            <p className="mt-0.5">{result.override.justification}</p>
          </div>
        )}
      </div>

      {/* Checks list */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {/* Failed checks first */}
        {failedChecks.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-medium uppercase tracking-wider text-destructive">
              {t("failedChecks", { count: failedChecks.length })}
            </h3>
            {failedChecks.map((check) => (
              <QACheckItem
                key={check.check_name}
                check={check}
                isOverridden={overriddenNames.has(check.check_name)}
              />
            ))}
          </div>
        )}

        {/* Passed checks (collapsible) */}
        {passedChecks.length > 0 && (
          <div className={failedChecks.length > 0 ? "mt-4" : ""}>
            <button
              type="button"
              onClick={() => setShowPassing((v) => !v)}
              className="flex w-full items-center justify-between text-xs font-medium uppercase tracking-wider text-status-success"
            >
              {t("passedChecks", { count: passedChecks.length })}
              {showPassing ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>
            {showPassing && (
              <div className="mt-2 space-y-2">
                {passedChecks.map((check) => (
                  <QACheckItem key={check.check_name} check={check} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Visual QA section */}
      {html && entityType && entityId ? (
        <div className="border-t border-border px-4 py-3">
          <VisualQAPanelTab
            html={html}
            entityType={entityType}
            entityId={entityId}
          />
        </div>
      ) : null}

      {/* Chaos testing section */}
      {html ? (
        <div className="border-t border-border px-4 py-3">
          <ChaosTestPanel html={html} />
        </div>
      ) : null}

      {/* Property testing section */}
      <div className="border-t border-border px-4 py-3">
        <PropertyTestPanel />
      </div>

      {/* Outlook Advisor section */}
      {html ? (
        <div className="border-t border-border px-4 py-3">
          <OutlookAdvisorPanel html={html} onHtmlUpdate={onHtmlUpdate} />
        </div>
      ) : null}

      {/* CSS Compiler section */}
      {html ? (
        <div className="border-t border-border px-4 py-3">
          <CSSCompilerPanel html={html} onHtmlUpdate={onHtmlUpdate} />
        </div>
      ) : null}

      {/* Gmail Intelligence section */}
      {html ? (
        <div className="border-t border-border px-4 py-3">
          <GmailPredictionPanel html={html} onHtmlUpdate={onHtmlUpdate} />
        </div>
      ) : null}

      {/* Override button (developer+ only, failing results only) */}
      {canOverride && (
        <div className="border-t border-border px-4 py-3">
          <button
            type="button"
            onClick={() => setOverrideOpen(true)}
            className="w-full rounded-md border border-status-warning bg-badge-warning-bg px-3 py-2 text-sm font-medium text-badge-warning-text transition-colors hover:opacity-80"
          >
            {t("overrideButton")}
          </button>
        </div>
      )}

      {/* Override dialog */}
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
