"use client";

import { useTranslations } from "next-intl";
import type { FailurePatternResponse } from "@/types/failure-patterns";

interface FailurePatternTableProps {
  patterns: FailurePatternResponse[];
  onSelect: (pattern: FailurePatternResponse) => void;
}

function confidenceBadge(confidence: number | null): {
  label: string;
  className: string;
} {
  if (confidence === null)
    return { label: "-", className: "text-foreground-muted" };
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

export function FailurePatternTable({
  patterns,
  onSelect,
}: FailurePatternTableProps) {
  const t = useTranslations("failurePatterns");

  if (patterns.length === 0) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg p-8 text-center">
        <p className="text-sm text-foreground-muted">
          {t("noMatchingPatterns")}
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-card-border">
      <table className="w-full text-sm">
        <thead className="bg-surface-muted">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-foreground-muted">
              {t("agent")}
            </th>
            <th className="px-4 py-3 text-left font-medium text-foreground-muted">
              {t("qaCheck")}
            </th>
            <th className="px-4 py-3 text-left font-medium text-foreground-muted">
              {t("clients")}
            </th>
            <th className="px-4 py-3 text-left font-medium text-foreground-muted">
              {t("confidence")}
            </th>
            <th className="px-4 py-3 text-left font-medium text-foreground-muted">
              {t("lastSeen")}
            </th>
          </tr>
        </thead>
        <tbody>
          {patterns.map((pattern) => {
            const badge = confidenceBadge(pattern.confidence);
            return (
              <tr
                key={pattern.id}
                onClick={() => onSelect(pattern)}
                className="cursor-pointer border-b border-card-border transition-colors hover:bg-surface-hover"
              >
                <td className="px-4 py-3">
                  <span className="rounded bg-surface-muted px-2 py-0.5 text-xs font-medium text-foreground">
                    {pattern.agent_name.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-foreground">
                  {pattern.qa_check.replace(/_/g, " ")}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {pattern.client_ids.slice(0, 3).map((c) => (
                      <span
                        key={c}
                        className="rounded bg-surface-muted px-1.5 py-0.5 text-xs text-foreground-muted"
                      >
                        {c.replace(/_/g, " ")}
                      </span>
                    ))}
                    {pattern.client_ids.length > 3 && (
                      <span className="text-xs text-foreground-muted">
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
                <td className="px-4 py-3 text-foreground-muted">
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
