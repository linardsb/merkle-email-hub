"use client";

import type { FailurePatternResponse } from "@/types/failure-patterns";

interface FailurePatternTableProps {
  patterns: FailurePatternResponse[];
  onSelect: (pattern: FailurePatternResponse) => void;
}

function confidenceBadge(confidence: number | null): {
  label: string;
  className: string;
} {
  if (confidence === null) return { label: "-", className: "text-foreground-muted" };
  if (confidence >= 0.7)
    return {
      label: `${Math.round(confidence * 100)}%`,
      className: "bg-badge-success-bg text-badge-success-text",
    };
  if (confidence >= 0.5)
    return {
      label: `${Math.round(confidence * 100)}%`,
      className: "bg-badge-warning-bg text-badge-warning-text",
    };
  return {
    label: `${Math.round(confidence * 100)}%`,
    className: "bg-badge-danger-bg text-badge-danger-text",
  };
}

export function FailurePatternTable({ patterns, onSelect }: FailurePatternTableProps) {
  if (patterns.length === 0) {
    return (
      <div className="border-card-border bg-card-bg rounded-lg border p-8 text-center">
        <p className="text-foreground-muted text-sm">{"No patterns match the current filters"}</p>
      </div>
    );
  }

  return (
    <div className="border-card-border overflow-hidden rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-surface-muted">
          <tr>
            <th className="text-foreground-muted px-4 py-3 text-left font-medium">{"Agent"}</th>
            <th className="text-foreground-muted px-4 py-3 text-left font-medium">{"QA Check"}</th>
            <th className="text-foreground-muted px-4 py-3 text-left font-medium">{"Clients"}</th>
            <th className="text-foreground-muted px-4 py-3 text-left font-medium">
              {"Confidence"}
            </th>
            <th className="text-foreground-muted px-4 py-3 text-left font-medium">{"Last Seen"}</th>
          </tr>
        </thead>
        <tbody>
          {patterns.map((pattern) => {
            const badge = confidenceBadge(pattern.confidence ?? null);
            return (
              <tr
                key={pattern.id}
                onClick={() => onSelect(pattern)}
                className="border-card-border hover:bg-surface-hover cursor-pointer border-b transition-colors"
              >
                <td className="px-4 py-3">
                  <span className="bg-surface-muted text-foreground rounded px-2 py-0.5 text-xs font-medium">
                    {pattern.agent_name.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="text-foreground px-4 py-3">{pattern.qa_check.replace(/_/g, " ")}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {pattern.client_ids.slice(0, 3).map((c) => (
                      <span
                        key={c}
                        className="bg-surface-muted text-foreground-muted rounded px-1.5 py-0.5 text-xs"
                      >
                        {c.replace(/_/g, " ")}
                      </span>
                    ))}
                    {pattern.client_ids.length > 3 && (
                      <span className="text-foreground-muted text-xs">
                        +{pattern.client_ids.length - 3}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {badge.label !== "-" ? (
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}
                    >
                      {badge.label}
                    </span>
                  ) : (
                    <span className="text-foreground-muted">-</span>
                  )}
                </td>
                <td className="text-foreground-muted px-4 py-3">
                  {new Date(pattern.last_seen).toLocaleDateString()}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
