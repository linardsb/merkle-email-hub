"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "../icons";
import { useQAResults } from "@/hooks/use-qa";

const PAGE_SIZE = 10;

function StatusBadge({ passed, hasOverride }: { passed: boolean; hasOverride: boolean }) {
  if (hasOverride) {
    return (
      <span className="bg-badge-warning-bg text-badge-warning-text rounded-full px-2 py-0.5 text-xs font-medium">
        {"Overridden"}
      </span>
    );
  }
  if (passed) {
    return (
      <span className="bg-badge-success-bg text-badge-success-text rounded-full px-2 py-0.5 text-xs font-medium">
        {"Passed"}
      </span>
    );
  }
  return (
    <span className="bg-badge-danger-bg text-badge-danger-text rounded-full px-2 py-0.5 text-xs font-medium">
      {"Failed"}
    </span>
  );
}

export function RecentResultsTable() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQAResults({ page, pageSize: PAGE_SIZE });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="bg-surface-muted h-10 animate-pulse rounded" />
        ))}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <p className="text-foreground-muted py-8 text-center text-sm">
        {"Run QA checks on your templates to see intelligence data here."}
      </p>
    );
  }

  return (
    <div>
      <div className="border-card-border overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-border bg-surface-muted border-b">
              <th className="text-foreground-muted px-4 py-3 text-left font-medium">{"Status"}</th>
              <th className="text-foreground-muted px-4 py-3 text-left font-medium">{"Score"}</th>
              <th className="text-foreground-muted px-4 py-3 text-left font-medium">{"Checks"}</th>
              <th className="text-foreground-muted px-4 py-3 text-left font-medium">{"Date"}</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((result) => (
              <tr
                key={result.id}
                className="border-border hover:bg-surface-hover border-b last:border-0"
              >
                <td className="px-4 py-3">
                  <StatusBadge passed={result.passed} hasOverride={Boolean(result.override)} />
                </td>
                <td className="text-foreground px-4 py-3 font-medium">
                  {Math.round(result.overall_score * 100)}%
                </td>
                <td className="text-foreground-muted px-4 py-3">
                  {result.checks_passed}/{result.checks_total}
                </td>
                <td className="text-foreground-muted px-4 py-3">
                  {new Date(result.created_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-foreground-muted text-sm">{`Page ${page} of ${totalPages}`}</p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="border-card-border bg-card-bg text-foreground hover:bg-surface-hover flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              {"Previous"}
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="border-card-border bg-card-bg text-foreground hover:bg-surface-hover flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              {"Next"}
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
