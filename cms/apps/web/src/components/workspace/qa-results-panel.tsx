"use client";

import { useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { X, ShieldCheck, ShieldAlert, ChevronDown, ChevronUp } from "../icons";
import { QACheckItem } from "./qa-check-item";
import { QAOverrideDialog } from "./qa-override-dialog";
import { VisualQAPanelTab } from "@/components/visual-qa/visual-qa-panel-tab";
import { CSSAuditPanel } from "@/components/qa/CSSAuditPanel";
import { ChaosTestPanel } from "@/components/qa/ChaosTestPanel";
import { PropertyTestPanel } from "@/components/qa/PropertyTestPanel";
import { OutlookAdvisorPanel } from "@/components/outlook/OutlookAdvisorPanel";
import { CSSCompilerPanel } from "@/components/email-engine/CSSCompilerPanel";
import { GmailPredictionPanel } from "@/components/gmail/GmailPredictionPanel";
import { OntologySyncPanel } from "@/components/knowledge/OntologySyncPanel";
import { CompetitiveReportPanel } from "@/components/knowledge/CompetitiveReportPanel";
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
  /** Callback to highlight a section in the builder canvas */
  onHighlightSection?: (sectionId: string) => void;
}

export function QAResultsPanel({
  result,
  onClose,
  onOverrideSuccess,
  html,
  entityType,
  entityId,
  onHtmlUpdate,
  onHighlightSection,
}: QAResultsPanelProps) {
  const session = useSession();
  const userRole = session.data?.user?.role;
  const canOverride =
    !result.passed && !result.override && (userRole === "admin" || userRole === "developer");

  const [overrideOpen, setOverrideOpen] = useState(false);
  const [showPassing, setShowPassing] = useState(false);

  const scorePercent = Math.round(result.overall_score * 100);
  const checks = result.checks ?? [];
  const failedChecks = useMemo(() => checks.filter((c) => !c.passed), [checks]);
  const passedChecks = useMemo(() => checks.filter((c) => c.passed), [checks]);
  const cssAuditCheck = useMemo(() => checks.find((c) => c.check_name === "css_audit"), [checks]);
  const overriddenNames = useMemo(
    () => new Set(result.override?.checks_overridden ?? []),
    [result.override?.checks_overridden],
  );

  return (
    <div className="border-border bg-card flex h-full w-80 flex-col border-l">
      {/* Header */}
      <div className="border-border flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          {result.passed || result.override ? (
            <ShieldCheck className="text-status-success h-5 w-5" />
          ) : (
            <ShieldAlert className="text-destructive h-5 w-5" />
          )}
          <h2 className="text-foreground text-sm font-semibold">{"QA Results"}</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={"Close"}
          className="text-muted-foreground hover:bg-accent hover:text-foreground rounded p-1 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Score summary */}
      <div className="border-border border-b px-4 py-3">
        <div className="flex items-baseline justify-between">
          <span className="text-foreground text-2xl font-bold">{scorePercent}%</span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              result.passed || result.override
                ? "bg-badge-success-bg text-badge-success-text"
                : "bg-badge-danger-bg text-badge-danger-text"
            }`}
          >
            {result.passed ? "Passed" : result.override ? "Overridden" : "Failed"}
          </span>
        </div>
        <p className="text-muted-foreground mt-1 text-xs">
          {`${result.checks_passed} of ${result.checks_total} checks passed`}
        </p>

        {/* Override info */}
        {result.override && (
          <div className="border-status-warning/30 bg-badge-warning-bg text-muted-foreground mt-2 rounded border px-2.5 py-2 text-xs">
            <p className="text-badge-warning-text font-medium">{"Override applied"}</p>
            <p className="mt-0.5">{result.override.justification}</p>
          </div>
        )}
      </div>

      {/* Checks list */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {/* Failed checks first */}
        {failedChecks.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-destructive text-xs font-medium tracking-wider uppercase">
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

        {/* Passed checks (collapsible) */}
        {passedChecks.length > 0 && (
          <div className={failedChecks.length > 0 ? "mt-4" : ""}>
            <button
              type="button"
              onClick={() => setShowPassing((v) => !v)}
              className="text-status-success flex w-full items-center justify-between text-xs font-medium tracking-wider uppercase"
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

      {/* CSS Compatibility Audit */}
      {cssAuditCheck && (
        <div className="border-border border-t px-4 py-3">
          <CSSAuditPanel check={cssAuditCheck} />
        </div>
      )}

      {/* Visual QA section */}
      {html && entityType && entityId ? (
        <div className="border-border border-t px-4 py-3">
          <VisualQAPanelTab html={html} entityType={entityType} entityId={entityId} />
        </div>
      ) : null}

      {/* Chaos testing section */}
      {html ? (
        <div className="border-border border-t px-4 py-3">
          <ChaosTestPanel html={html} />
        </div>
      ) : null}

      {/* Property testing section */}
      <div className="border-border border-t px-4 py-3">
        <PropertyTestPanel />
      </div>

      {/* Outlook Advisor section */}
      {html ? (
        <div className="border-border border-t px-4 py-3">
          <OutlookAdvisorPanel html={html} onHtmlUpdate={onHtmlUpdate} />
        </div>
      ) : null}

      {/* CSS Compiler section */}
      {html ? (
        <div className="border-border border-t px-4 py-3">
          <CSSCompilerPanel html={html} onHtmlUpdate={onHtmlUpdate} />
        </div>
      ) : null}

      {/* Gmail Intelligence section */}
      {html ? (
        <div className="border-border border-t px-4 py-3">
          <GmailPredictionPanel html={html} onHtmlUpdate={onHtmlUpdate} />
        </div>
      ) : null}

      {/* Ontology Sync section */}
      <div className="border-border border-t px-4 py-3">
        <OntologySyncPanel />
      </div>

      {/* Competitive Intelligence section */}
      <div className="border-border border-t px-4 py-3">
        <CompetitiveReportPanel />
      </div>

      {/* Override button (developer+ only, failing results only) */}
      {canOverride && (
        <div className="border-border border-t px-4 py-3">
          <button
            type="button"
            onClick={() => setOverrideOpen(true)}
            className="border-status-warning bg-badge-warning-bg text-badge-warning-text w-full rounded-md border px-3 py-2 text-sm font-medium transition-colors hover:opacity-80"
          >
            {"Override Failing Checks"}
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
