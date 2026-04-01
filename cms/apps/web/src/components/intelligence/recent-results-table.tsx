"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "../icons";
import { useQAResults } from "@/hooks/use-qa";

const PAGE_SIZE = 10;

function StatusBadge({
  passed,
  hasOverride,
}: {
  passed: boolean;
  hasOverride: boolean;
}) {
  if (hasOverride) {
    return (
      <span className="rounded-full bg-badge-warning-bg px-2 py-0.5 text-xs font-medium text-badge-warning-text">
        {"Overridden"}
      </span>
    );
  }
  if (passed) {
    return (
      <span className="rounded-full bg-badge-success-bg px-2 py-0.5 text-xs font-medium text-badge-success-text">
        {"Passed"}
      </span>
    );
  }
  return (
    <span className="rounded-full bg-badge-danger-bg px-2 py-0.5 text-xs font-medium text-badge-danger-text">
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
          <div
            key={i}
            className="h-10 animate-pulse rounded bg-surface-muted"
          />
        ))}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-foreground-muted">
        {"Run QA checks on your templates to see intelligence data here."}
      </p>
    );
  }

  return (
    <div>
      <div className="overflow-hidden rounded-lg border border-card-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-muted">
              <th className="px-4 py-3 text-left font-medium text-foreground-muted">
                {"Status"}
              </th>
              <th className="px-4 py-3 text-left font-medium text-foreground-muted">
                {"Score"}
              </th>
              <th className="px-4 py-3 text-left font-medium text-foreground-muted">
                {"Checks"}
              </th>
              <th className="px-4 py-3 text-left font-medium text-foreground-muted">
                {"Date"}
              </th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((result) => (
              <tr
                key={result.id}
                className="border-b border-border last:border-0 hover:bg-surface-hover"
              >
                <td className="px-4 py-3">
                  <StatusBadge
                    passed={result.passed}
                    hasOverride={!!result.override}
                  />
                </td>
                <td className="px-4 py-3 font-medium text-foreground">
                  {Math.round(result.overall_score * 100)}%
                </td>
                <td className="px-4 py-3 text-foreground-muted">
                  {result.checks_passed}/{result.checks_total}
                </td>
                <td className="px-4 py-3 text-foreground-muted">
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
          <p className="text-sm text-foreground-muted">
            {`Page ${page} of ${totalPages}`}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="flex items-center gap-1 rounded-md border border-card-border bg-card-bg px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              {"Previous"}
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="flex items-center gap-1 rounded-md border border-card-border bg-card-bg px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
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
