"use client";

import Link from "next/link";
import { AlertTriangle } from "../icons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useFailurePatterns } from "@/hooks/use-failure-patterns";

export function TopFailurePatternsCard() {
  const { data: patterns, isLoading } = useFailurePatterns({
    page: 1,
    pageSize: 5,
  });

  if (isLoading) {
    return <Skeleton className="h-48 rounded-lg border border-card-border" />;
  }

  const items = patterns?.items ?? [];
  const totalPatterns = patterns?.total ?? 0;

  if (totalPatterns === 0) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg p-6">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-foreground-muted" />
          <h2 className="text-lg font-semibold text-foreground">
            {"Top Failure Patterns"}
          </h2>
        </div>
        <p className="mt-2 text-sm text-foreground-muted">
          {"No failure patterns detected yet."}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-foreground-muted" />
          <h2 className="text-lg font-semibold text-foreground">
            {"Top Failure Patterns"}
          </h2>
        </div>
        <Link
          href="/renderings?tab=patterns"
          className="text-sm text-foreground-accent hover:underline"
        >
          {"View all patterns"}
        </Link>
      </div>
      <p className="mt-1 text-sm text-foreground-muted">
        {`${totalPatterns} total patterns tracked across agents`}
      </p>

      <div className="mt-4 space-y-2">
        {items.map((pattern, i) => (
          <div
            key={i}
            className="flex items-center justify-between rounded border border-card-border px-3 py-2"
          >
            <div className="flex-1 truncate">
              <span className="text-sm font-medium text-foreground">
                {pattern.agent_name.replace(/_/g, " ")}
              </span>
              <span className="mx-2 text-foreground-muted">/</span>
              <span className="text-sm text-foreground-muted">
                {pattern.qa_check.replace(/_/g, " ")}
              </span>
            </div>
            <span className="ml-2 rounded-full bg-status-danger/10 px-2 py-0.5 text-xs font-medium text-status-danger">
              {pattern.frequency ?? 1}x
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
