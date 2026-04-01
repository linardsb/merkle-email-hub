"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "../icons";
import type {
  DeliverabilityScoreResponse,
  DeliverabilityDimension,
  DeliverabilityIssue,
} from "@/types/gmail-intelligence";

const SEVERITY_STYLES: Record<string, string> = {
  error: "bg-badge-danger-bg text-badge-danger-text",
  warning: "bg-badge-warning-bg text-badge-warning-text",
  info: "bg-badge-info-bg text-badge-info-text",
};

function scoreColor(score: number): string {
  if (score >= 80) return "text-status-success";
  if (score >= 60) return "text-status-warning";
  return "text-status-error";
}

function DimensionBar({ dim }: { dim: DeliverabilityDimension }) {
  const [expanded, setExpanded] = useState(false);
  const pct = dim.max_score > 0 ? (dim.score / dim.max_score) * 100 : 0;

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-xs"
      >
        <span className="text-foreground-muted">{dim.name}</span>
        <div className="flex items-center gap-1.5">
          <span className="text-foreground">
            {dim.score}/{dim.max_score}
          </span>
          {dim.issues.length > 0 &&
            (expanded ? (
              <ChevronUp className="h-3 w-3 text-foreground-muted" />
            ) : (
              <ChevronDown className="h-3 w-3 text-foreground-muted" />
            ))}
        </div>
      </button>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-accent-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      {expanded && dim.issues.length > 0 && (
        <div className="mt-1.5 space-y-1">
          {dim.issues.map((issue: DeliverabilityIssue, i: number) => (
            <div key={i} className="rounded border border-border bg-card p-2">
              <div className="flex items-start gap-1.5">
                <span
                  className={`mt-0.5 shrink-0 rounded px-1 py-0.5 text-[9px] font-medium ${SEVERITY_STYLES[issue.severity] ?? SEVERITY_STYLES.info}`}
                >
                  {issue.severity}
                </span>
                <div className="min-w-0">
                  <p className="text-[10px] text-foreground">
                    {issue.description}
                  </p>
                  <p className="mt-0.5 text-[10px] text-status-success">
                    {"Fix"}: {issue.fix}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface DeliverabilityGaugeProps {
  result: DeliverabilityScoreResponse;
}

export function DeliverabilityGauge({ result }: DeliverabilityGaugeProps) {
  return (
    <div className="space-y-2.5">
      {/* Overall score */}
      <div className="flex items-center gap-2">
        <span className={`text-2xl font-bold ${scoreColor(result.score)}`}>
          {result.score}
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
            result.passed
              ? "bg-badge-success-bg text-badge-success-text"
              : "bg-badge-danger-bg text-badge-danger-text"
          }`}
        >
          {result.passed ? "Passed" : "Failed"}
        </span>
      </div>

      {/* Summary */}
      <p className="text-xs text-foreground-muted">{result.summary}</p>

      {/* Dimension bars */}
      {result.dimensions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-medium text-foreground-muted">
            {"Dimensions"}
          </h4>
          {result.dimensions.map((dim) => (
            <DimensionBar key={dim.name} dim={dim} />
          ))}
        </div>
      )}
    </div>
  );
}
