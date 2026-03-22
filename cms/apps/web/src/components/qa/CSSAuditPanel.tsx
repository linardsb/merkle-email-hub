"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronUp, ShieldCheck, AlertTriangle, XCircle, Info } from "lucide-react";
import type { QACheckResult, CSSAuditDetails } from "@/types/qa";

interface CSSAuditPanelProps {
  check: QACheckResult | undefined;
}

const STATUS_COLORS: Record<string, string> = {
  supported: "bg-status-success/20 text-status-success",
  converted: "bg-status-warning/20 text-status-warning",
  removed: "bg-destructive/20 text-destructive",
  partial: "bg-badge-info-bg text-badge-info-text",
};

const STATUS_LABELS: Record<string, string> = {
  supported: "\u2713",
  converted: "~",
  removed: "\u2717",
  partial: "\u25D0",
};

type FilterMode = "all" | "errors" | "warnings";

export function CSSAuditPanel({ check }: CSSAuditPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [filter, setFilter] = useState<FilterMode>("all");

  const details = useMemo<CSSAuditDetails | null>(() => {
    if (!check?.details) return null;
    try {
      return JSON.parse(check.details) as CSSAuditDetails;
    } catch {
      return null;
    }
  }, [check?.details]);

  if (!check || !details) return null;

  const clients = Object.keys(details.compatibility_matrix);
  const firstClient = clients[0];
  const allProperties = firstClient !== undefined
    ? Object.keys(details.compatibility_matrix[firstClient] ?? {}).sort()
    : [];

  const filteredProperties = allProperties.filter((prop) => {
    if (filter === "all") return true;
    return clients.some((client) => {
      const status = details.compatibility_matrix[client]?.[prop];
      if (filter === "errors") return status === "removed";
      if (filter === "warnings") return status === "converted" || status === "partial";
      return true;
    });
  });

  const formatClientName = (id: string) =>
    id.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-sm font-medium text-foreground"
      >
        <span className="flex items-center gap-2">
          {check.passed ? (
            <ShieldCheck className="h-4 w-4 text-status-success" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-status-warning" />
          )}
          CSS Compatibility
          <span className="text-xs text-muted-foreground">
            {details.overall_coverage_score}%
          </span>
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3">
          {/* Coverage bars */}
          <div className="space-y-1.5">
            {clients.map((client) => (
              <div key={client} className="flex items-center gap-2">
                <span className="w-24 truncate text-xs text-muted-foreground">
                  {formatClientName(client)}
                </span>
                <div className="h-1.5 flex-1 rounded-full bg-muted">
                  <div
                    className={`h-1.5 rounded-full transition-all ${
                      (details.client_coverage_score[client] ?? 0) >= 90
                        ? "bg-status-success"
                        : (details.client_coverage_score[client] ?? 0) >= 70
                          ? "bg-status-warning"
                          : "bg-destructive"
                    }`}
                    style={{ width: `${details.client_coverage_score[client] ?? 0}%` }}
                  />
                </div>
                <span className="w-10 text-right text-xs text-muted-foreground">
                  {details.client_coverage_score[client] ?? 0}%
                </span>
              </div>
            ))}
          </div>

          {/* Filter buttons */}
          <div className="flex gap-1">
            {(["all", "errors", "warnings"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setFilter(mode)}
                className={`rounded px-2 py-0.5 text-xs transition-colors ${
                  filter === mode
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {mode === "all" ? `All (${allProperties.length})` :
                 mode === "errors" ? `Errors (${details.error_count})` :
                 `Warnings (${details.warning_count})`}
              </button>
            ))}
          </div>

          {/* Matrix table */}
          {filteredProperties.length > 0 && (
            <div className="overflow-x-auto rounded border border-border">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/50">
                    <th className="px-2 py-1.5 text-left font-medium text-muted-foreground">
                      Property
                    </th>
                    {clients.map((client) => (
                      <th
                        key={client}
                        className="px-2 py-1.5 text-center font-medium text-muted-foreground"
                        title={formatClientName(client)}
                      >
                        {formatClientName(client).slice(0, 8)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredProperties.map((prop) => (
                    <tr key={prop} className="border-b border-border last:border-0">
                      <td className="px-2 py-1 font-mono text-foreground">{prop}</td>
                      {clients.map((client) => {
                        const status = details.compatibility_matrix[client]?.[prop] ?? "supported";
                        return (
                          <td key={client} className="px-2 py-1 text-center">
                            <span
                              className={`inline-flex h-5 w-5 items-center justify-center rounded text-xs font-medium ${STATUS_COLORS[status] ?? ""}`}
                              title={`${prop}: ${status} in ${formatClientName(client)}`}
                            >
                              {STATUS_LABELS[status] ?? "?"}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Conversions detail */}
          {details.conversions.length > 0 && (
            <details className="text-xs">
              <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
                {details.conversions.length} conversion{details.conversions.length > 1 ? "s" : ""} applied
              </summary>
              <div className="mt-1.5 space-y-1">
                {details.conversions.map((conv, i) => (
                  <div key={i} className="rounded border border-border px-2 py-1.5">
                    <div className="flex items-center gap-1">
                      <span className="font-mono text-destructive line-through">
                        {conv.original_property}: {conv.original_value}
                      </span>
                      <span className="text-muted-foreground">&rarr;</span>
                      <span className="font-mono text-status-success">
                        {conv.replacement_property}: {conv.replacement_value}
                      </span>
                    </div>
                    <p className="mt-0.5 text-muted-foreground">{conv.reason}</p>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Issues summary */}
          {details.issues.length > 0 && (
            <div className="space-y-1">
              {details.issues.map((issue, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs">
                  {issue.includes("no fallback") ? (
                    <XCircle className="mt-0.5 h-3 w-3 shrink-0 text-destructive" />
                  ) : issue.includes("converted") ? (
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-status-warning" />
                  ) : (
                    <Info className="mt-0.5 h-3 w-3 shrink-0 text-badge-info-text" />
                  )}
                  <span className="text-muted-foreground">{issue}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
