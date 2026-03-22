"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ClientGateResult } from "@/types/rendering-gate";

const TIER_LABELS: Record<string, string> = {
  tier_1: "Tier 1",
  tier_2: "Tier 2",
  tier_3: "Tier 3",
};

interface Props {
  result: ClientGateResult;
}

export function GateClientRow({ result }: Props) {
  const [expanded, setExpanded] = useState(!result.passed);
  const hasDetails = result.blocking_reasons.length > 0 || result.remediation.length > 0;

  const barColor = result.passed ? "bg-status-success" : "bg-status-danger";
  const barWidth = Math.max(0, Math.min(100, result.confidence_score));
  const thresholdLeft = Math.max(0, Math.min(100, result.threshold));

  return (
    <div className="rounded-md border border-card-border bg-card-bg">
      {/* Header row */}
      <button
        type="button"
        onClick={() => hasDetails && setExpanded((prev) => !prev)}
        disabled={!hasDetails}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm"
      >
        {/* Expand chevron */}
        <span className="w-4 shrink-0 text-foreground-muted">
          {hasDetails ? (
            expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />
          ) : null}
        </span>

        {/* Client name + tier */}
        <span className="w-40 shrink-0">
          <span className="font-medium text-foreground">{result.client_name}</span>
          <span className="ml-1.5 text-xs text-foreground-muted">
            {TIER_LABELS[result.tier] ?? result.tier}
          </span>
        </span>

        {/* Confidence bar */}
        <span className="relative flex-1">
          <span className="block h-2 w-full rounded-full bg-surface-muted">
            <span
              className={`block h-2 rounded-full ${barColor} transition-all`}
              style={{ width: `${barWidth}%` }}
            />
          </span>
          {/* Threshold marker */}
          <span
            className="absolute top-0 h-2 w-0.5 bg-foreground-muted"
            style={{ left: `${thresholdLeft}%` }}
            title={`Threshold: ${result.threshold}%`}
          />
        </span>

        {/* Score */}
        <span className="w-14 shrink-0 text-right font-mono text-xs text-foreground-muted">
          {result.confidence_score.toFixed(0)}%
        </span>

        {/* Pass/fail badge */}
        <span
          className={`w-14 shrink-0 rounded-full px-2 py-0.5 text-center text-xs font-medium ${
            result.passed
              ? "bg-badge-success-bg text-badge-success-text"
              : "bg-badge-danger-bg text-badge-danger-text"
          }`}
        >
          {result.passed ? "Pass" : "Fail"}
        </span>
      </button>

      {/* Expanded details */}
      {expanded && hasDetails && (
        <div className="border-t border-card-border px-3 py-2.5 pl-10 text-xs">
          {result.blocking_reasons.length > 0 && (
            <div className="mb-2">
              <p className="mb-1 font-medium text-foreground">Blocking Reasons</p>
              <ul className="list-inside list-disc space-y-0.5 text-foreground-muted">
                {result.blocking_reasons.map((reason, i) => (
                  <li key={i}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
          {result.remediation.length > 0 && (
            <div>
              <p className="mb-1 font-medium text-foreground">Remediation</p>
              <ul className="list-inside list-disc space-y-0.5 text-foreground-muted">
                {result.remediation.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
