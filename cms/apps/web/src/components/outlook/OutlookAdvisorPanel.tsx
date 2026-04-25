"use client";

import { useState } from "react";
import { Search, ChevronDown, ChevronUp, Loader2, ArrowRight } from "../icons";
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

const DEP_TYPE_LABELS: Record<string, string> = {
  vml_shape: "VML Shape",
  ghost_table: "Ghost Table",
  mso_conditional: "MSO Conditional",
  mso_css: "MSO CSS",
  dpi_image: "DPI Image",
  external_class: "External Class",
  word_wrap_hack: "Word Wrap Hack",
};

const SEVERITY_LABELS: Record<string, string> = { high: "High", medium: "Medium", low: "Low" };

const TARGET_LABELS: Record<string, string> = {
  new_outlook: "New Outlook Only",
  dual_support: "Dual Support",
  audit_only: "Audit Only",
};

const TARGET_OPTIONS = ["new_outlook", "dual_support", "audit_only"] as const;

function formatKB(bytes: number): string {
  return (bytes / 1024).toFixed(1);
}

function DependencyRow({ dep }: { dep: OutlookDependencySchema }) {
  const [expanded, setExpanded] = useState(false);

  const typeLabel = DEP_TYPE_LABELS[dep.type] ?? dep.type;

  const severityStyle = SEVERITY_STYLES[dep.severity] ?? SEVERITY_STYLES.low;

  return (
    <div className="border-border bg-card rounded border">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-2.5 py-2 text-left text-xs"
      >
        <div className="flex items-center gap-1.5">
          <span
            className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${severityStyle}`}
          >
            {SEVERITY_LABELS[dep.severity] ?? dep.severity}
          </span>
          <span className="bg-surface-muted text-foreground-muted rounded px-1.5 py-0.5 text-[10px] font-medium">
            {typeLabel}
          </span>
          <span className="text-foreground-muted">{`Line ${dep.line_number}`}</span>
        </div>
        {expanded ? (
          <ChevronUp className="text-foreground-muted h-3 w-3" />
        ) : (
          <ChevronDown className="text-foreground-muted h-3 w-3" />
        )}
      </button>

      {expanded && (
        <div className="border-border space-y-1.5 border-t px-2.5 py-2">
          <code className="bg-surface-muted text-foreground-muted block overflow-x-auto rounded p-1.5 font-mono text-[10px]">
            {dep.code_snippet}
          </code>
          <p className="text-foreground-muted text-[10px]">{dep.location}</p>
          {dep.modern_replacement && (
            <p className="text-status-success text-[10px]">
              {`Modern alternative: ${dep.modern_replacement}`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function OutlookAdvisorPanel({ html, onHtmlUpdate }: OutlookAdvisorPanelProps) {
  const { trigger, data, isMutating } = useOutlookAnalysis();
  const {
    trigger: modernizeTrigger,
    data: modernizeData,
    isMutating: isModernizing,
  } = useOutlookModernize();
  const [target, setTarget] = useState<(typeof TARGET_OPTIONS)[number]>("dual_support");
  const [showDeps, setShowDeps] = useState(false);

  return (
    <div className="bg-surface-muted rounded-lg p-3">
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Search className="text-foreground-muted h-4 w-4" />
          <h3 className="text-foreground-muted text-xs font-medium uppercase tracking-wider">
            {"Outlook Advisor"}
          </h3>
        </div>
        <button
          type="button"
          disabled={isMutating}
          onClick={() => trigger({ html })}
          className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
        >
          {isMutating ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              {"Analyzing…"}
            </>
          ) : (
            "Analyze"
          )}
        </button>
      </div>

      {/* Empty state */}
      {!data && !isMutating && (
        <p className="text-foreground-muted text-xs">
          {"Analyze your email to detect Outlook Word-engine dependencies."}
        </p>
      )}

      {data && (
        <div className="space-y-3">
          {/* Summary stats */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="bg-card text-foreground rounded-full px-2 py-0.5 font-medium">
              {`${data.total_count} dependencies found`}
            </span>
            <span className="bg-card text-foreground-muted rounded-full px-2 py-0.5">
              {`${data.removable_count} removable`}
            </span>
            {data.byte_savings > 0 && (
              <span className="bg-badge-success-bg text-badge-success-text rounded-full px-2 py-0.5">
                {`${formatKB(data.byte_savings)} KB potential savings`}
              </span>
            )}
          </div>

          {/* Severity breakdown */}
          {data.dependencies.length > 0 && (
            <div className="flex gap-2 text-[10px]">
              {(["high", "medium", "low"] as const).map((sev) => {
                const count = data.dependencies.filter(
                  (d: OutlookDependencySchema) => d.severity === sev,
                ).length;
                if (count === 0) return null;
                return (
                  <span
                    key={sev}
                    className={`rounded-full px-2 py-0.5 font-medium ${SEVERITY_STYLES[sev]}`}
                  >
                    {count} {SEVERITY_LABELS[sev] ?? sev}
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
                className="text-foreground-muted flex w-full items-center justify-between text-xs font-medium"
              >
                <span>{`${data.dependencies.length} dependencies found`}</span>
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
              <h4 className="text-foreground-muted mb-1.5 text-xs font-medium">
                {"Migration Plan"}
              </h4>
              <MigrationTimeline plan={data.modernization_plan} />
            </div>
          )}

          {/* Modernize action */}
          {data.removable_count > 0 && (
            <div className="border-border bg-card space-y-2 rounded border p-2.5">
              <div className="flex items-center gap-2">
                <label className="text-foreground-muted text-xs">{"Target Mode"}</label>
                <select
                  value={target}
                  onChange={(e) => setTarget(e.target.value as typeof target)}
                  disabled={isModernizing}
                  className="border-border bg-surface-muted text-foreground rounded border px-1.5 py-0.5 text-xs disabled:opacity-50"
                >
                  {TARGET_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {TARGET_LABELS[opt] ?? opt}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                disabled={isModernizing}
                onClick={() => modernizeTrigger({ html, target })}
                className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
              >
                {isModernizing ? (
                  <>
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {"Modernizing…"}
                  </>
                ) : (
                  <>
                    <ArrowRight className="h-3 w-3" />
                    {"Modernize"}
                  </>
                )}
              </button>
            </div>
          )}

          {/* Post-modernize results */}
          {modernizeData && (
            <div className="border-status-success/30 bg-badge-success-bg space-y-1.5 rounded border p-2.5">
              <p className="text-badge-success-text text-xs font-medium">
                {`${modernizeData.changes_applied} changes applied · ${formatKB(modernizeData.bytes_saved)} KB saved`}
              </p>
              <div className="text-foreground-muted flex gap-3 text-[10px]">
                <span>{`Before: ${formatKB(modernizeData.bytes_before)} KB`}</span>
                <span>{`After: ${formatKB(modernizeData.bytes_after)} KB`}</span>
              </div>
              {onHtmlUpdate && modernizeData.changes_applied > 0 && (
                <button
                  type="button"
                  onClick={() => onHtmlUpdate(modernizeData.html)}
                  className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium transition-colors"
                >
                  {"Apply Changes"}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
