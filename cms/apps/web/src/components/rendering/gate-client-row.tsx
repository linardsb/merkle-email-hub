"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "../icons";
import type { ClientGateResult } from "@/types/rendering-gate";
import { ConfidenceBar } from "./confidence-bar";

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

  return (
    <div className="border-card-border bg-card-bg rounded-md border">
      {/* Header row */}
      <button
        type="button"
        onClick={() => hasDetails && setExpanded((prev) => !prev)}
        disabled={!hasDetails}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm"
      >
        {/* Expand chevron */}
        <span className="text-foreground-muted w-4 shrink-0">
          {hasDetails ? (
            expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )
          ) : null}
        </span>

        {/* Client name + tier */}
        <span className="w-40 shrink-0">
          <span className="text-foreground font-medium">{result.client_name}</span>
          <span className="text-foreground-muted ml-1.5 text-xs">
            {TIER_LABELS[result.tier] ?? result.tier}
          </span>
        </span>

        {/* Confidence bar */}
        <ConfidenceBar score={result.confidence_score} threshold={result.threshold} size="sm" />

        {/* Score */}
        <span className="text-foreground-muted w-14 shrink-0 text-right font-mono text-xs">
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
        <div className="border-card-border border-t px-3 py-2.5 pl-10 text-xs">
          {result.blocking_reasons.length > 0 && (
            <div className="mb-2">
              <p className="text-foreground mb-1 font-medium">Blocking Reasons</p>
              <ul className="text-foreground-muted list-inside list-disc space-y-0.5">
                {result.blocking_reasons.map((reason, i) => (
                  <li key={i}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
          {result.remediation.length > 0 && (
            <div>
              <p className="text-foreground mb-1 font-medium">Remediation</p>
              <ul className="text-foreground-muted list-inside list-disc space-y-0.5">
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
