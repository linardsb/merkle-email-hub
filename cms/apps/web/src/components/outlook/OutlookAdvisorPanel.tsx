"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Search,
  ChevronDown,
  ChevronUp,
  Loader2,
  ArrowRight,
} from "lucide-react";
import { useOutlookAnalysis, useOutlookModernize } from "@/hooks/use-outlook-analysis";
import { MigrationTimeline } from "./MigrationTimeline";
import type { OutlookDependencySchema } from "@/types/outlook";

interface OutlookAdvisorPanelProps {
  html: string;
  onHtmlUpdate?: (html: string) => void;
}

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-badge-danger-bg text-badge-danger-text",
  medium: "bg-badge-warning-bg text-badge-warning-text",
  low: "bg-badge-success-bg text-badge-success-text",
};

const TARGET_OPTIONS = ["new_outlook", "dual_support", "audit_only"] as const;

function formatKB(bytes: number): string {
  return (bytes / 1024).toFixed(1);
}

function DependencyRow({ dep }: { dep: OutlookDependencySchema }) {
  const t = useTranslations("outlookAdvisor");
  const [expanded, setExpanded] = useState(false);

  let typeLabel: string;
  try {
    typeLabel = t(`depTypes.${dep.type}`);
  } catch {
    typeLabel = dep.type;
  }

  const severityStyle = SEVERITY_STYLES[dep.severity] ?? SEVERITY_STYLES.low;
  const severityKey = `severity${dep.severity.charAt(0).toUpperCase()}${dep.severity.slice(1)}` as
    | "severityHigh"
    | "severityMedium"
    | "severityLow";

  return (
    <div className="rounded border border-border bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-2.5 py-2 text-left text-xs"
      >
        <div className="flex items-center gap-1.5">
          <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${severityStyle}`}>
            {t(severityKey)}
          </span>
          <span className="rounded bg-surface-muted px-1.5 py-0.5 text-[10px] font-medium text-foreground-muted">
            {typeLabel}
          </span>
          <span className="text-foreground-muted">
            {t("line", { number: dep.line_number })}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="h-3 w-3 text-foreground-muted" />
        ) : (
          <ChevronDown className="h-3 w-3 text-foreground-muted" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-border px-2.5 py-2 space-y-1.5">
          <code className="block overflow-x-auto rounded bg-surface-muted p-1.5 font-mono text-[10px] text-foreground-muted">
            {dep.code_snippet}
          </code>
          <p className="text-[10px] text-foreground-muted">{dep.location}</p>
          {dep.modern_replacement && (
            <p className="text-[10px] text-status-success">
              {t("modernReplacement", { replacement: dep.modern_replacement })}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function OutlookAdvisorPanel({ html, onHtmlUpdate }: OutlookAdvisorPanelProps) {
  const t = useTranslations("outlookAdvisor");
  const { trigger, data, isMutating } = useOutlookAnalysis();
  const {
    trigger: modernizeTrigger,
    data: modernizeData,
    isMutating: isModernizing,
  } = useOutlookModernize();
  const [target, setTarget] = useState<(typeof TARGET_OPTIONS)[number]>("dual_support");
  const [showDeps, setShowDeps] = useState(false);

  return (
    <div className="rounded-lg bg-surface-muted p-3">
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-foreground-muted" />
          <h3 className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
            {t("title")}
          </h3>
        </div>
        <button
          type="button"
          disabled={isMutating}
          onClick={() => trigger({ html })}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          {isMutating ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              {t("analyzing")}
            </>
          ) : (
            t("analyzeButton")
          )}
        </button>
      </div>

      {/* Empty state */}
      {!data && !isMutating && (
        <p className="text-xs text-foreground-muted">{t("noResults")}</p>
      )}

      {data && (
        <div className="space-y-3">
          {/* Summary stats */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-card px-2 py-0.5 font-medium text-foreground">
              {t("totalDependencies", { count: data.total_count })}
            </span>
            <span className="rounded-full bg-card px-2 py-0.5 text-foreground-muted">
              {t("removable", { count: data.removable_count })}
            </span>
            {data.byte_savings > 0 && (
              <span className="rounded-full bg-badge-success-bg px-2 py-0.5 text-badge-success-text">
                {t("byteSavings", { size: formatKB(data.byte_savings) })}
              </span>
            )}
          </div>

          {/* Severity breakdown */}
          {data.dependencies.length > 0 && (
            <div className="flex gap-2 text-[10px]">
              {(["high", "medium", "low"] as const).map((sev) => {
                const count = data.dependencies.filter(
                  (d: OutlookDependencySchema) => d.severity === sev
                ).length;
                if (count === 0) return null;
                return (
                  <span
                    key={sev}
                    className={`rounded-full px-2 py-0.5 font-medium ${SEVERITY_STYLES[sev]}`}
                  >
                    {count} {t(`severity${sev.charAt(0).toUpperCase()}${sev.slice(1)}` as "severityHigh" | "severityMedium" | "severityLow")}
                  </span>
                );
              })}
            </div>
          )}

          {/* Dependency list (collapsible) */}
          {data.dependencies.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowDeps((v) => !v)}
                className="flex w-full items-center justify-between text-xs font-medium text-foreground-muted"
              >
                <span>
                  {t("totalDependencies", { count: data.dependencies.length })}
                </span>
                {showDeps ? (
                  <ChevronUp className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
              </button>
              {showDeps && (
                <div className="mt-1.5 space-y-1.5">
                  {data.dependencies.map((dep: OutlookDependencySchema, i: number) => (
                    <DependencyRow key={`${dep.type}-${dep.line_number}-${i}`} dep={dep} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Migration timeline */}
          {data.modernization_plan.length > 0 && (
            <div>
              <h4 className="mb-1.5 text-xs font-medium text-foreground-muted">
                {t("migrationPlan")}
              </h4>
              <MigrationTimeline plan={data.modernization_plan} />
            </div>
          )}

          {/* Modernize action */}
          {data.removable_count > 0 && (
            <div className="rounded border border-border bg-card p-2.5 space-y-2">
              <div className="flex items-center gap-2">
                <label className="text-xs text-foreground-muted">
                  {t("targetLabel")}
                </label>
                <select
                  value={target}
                  onChange={(e) => setTarget(e.target.value as typeof target)}
                  disabled={isModernizing}
                  className="rounded border border-border bg-surface-muted px-1.5 py-0.5 text-xs text-foreground disabled:opacity-50"
                >
                  {TARGET_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {t(`target${opt === "new_outlook" ? "NewOutlook" : opt === "dual_support" ? "DualSupport" : "AuditOnly"}`)}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                disabled={isModernizing}
                onClick={() => modernizeTrigger({ html, target })}
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
              >
                {isModernizing ? (
                  <>
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {t("modernizing")}
                  </>
                ) : (
                  <>
                    <ArrowRight className="h-3 w-3" />
                    {t("modernizeButton")}
                  </>
                )}
              </button>
            </div>
          )}

          {/* Post-modernize results */}
          {modernizeData && (
            <div className="rounded border border-status-success/30 bg-badge-success-bg p-2.5 space-y-1.5">
              <p className="text-xs font-medium text-badge-success-text">
                {t("changesSummary", {
                  changes: modernizeData.changes_applied,
                  saved: formatKB(modernizeData.bytes_saved),
                })}
              </p>
              <div className="flex gap-3 text-[10px] text-foreground-muted">
                <span>{t("beforeSize", { size: formatKB(modernizeData.bytes_before) })}</span>
                <span>{t("afterSize", { size: formatKB(modernizeData.bytes_after) })}</span>
              </div>
              {onHtmlUpdate && modernizeData.changes_applied > 0 && (
                <button
                  type="button"
                  onClick={() => onHtmlUpdate(modernizeData.html)}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-2 py-0.5 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover"
                >
                  {t("applyButton")}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
