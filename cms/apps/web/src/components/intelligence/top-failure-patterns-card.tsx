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
    return <Skeleton className="border-card-border h-48 rounded-lg border" />;
  }

  const items = patterns?.items ?? [];
  const totalPatterns = patterns?.total ?? 0;

  if (totalPatterns === 0) {
    return (
      <div className="border-card-border bg-card-bg rounded-lg border p-6">
        <div className="flex items-center gap-2">
          <AlertTriangle className="text-foreground-muted h-5 w-5" />
          <h2 className="text-foreground text-lg font-semibold">{"Top Failure Patterns"}</h2>
        </div>
        <p className="text-foreground-muted mt-2 text-sm">{"No failure patterns detected yet."}</p>
      </div>
    );
  }

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="text-foreground-muted h-5 w-5" />
          <h2 className="text-foreground text-lg font-semibold">{"Top Failure Patterns"}</h2>
        </div>
        <Link
          href="/renderings?tab=patterns"
          className="text-foreground-accent text-sm hover:underline"
        >
          {"View all patterns"}
        </Link>
      </div>
      <p className="text-foreground-muted mt-1 text-sm">
        {`${totalPatterns} total patterns tracked across agents`}
      </p>

      <div className="mt-4 space-y-2">
        {items.map((pattern, i) => (
          <div
            key={i}
            className="border-card-border flex items-center justify-between rounded border px-3 py-2"
          >
            <div className="flex-1 truncate">
              <span className="text-foreground text-sm font-medium">
                {pattern.agent_name.replace(/_/g, " ")}
              </span>
              <span className="text-foreground-muted mx-2">/</span>
              <span className="text-foreground-muted text-sm">
                {pattern.qa_check.replace(/_/g, " ")}
              </span>
            </div>
            <span className="bg-status-danger/10 text-status-danger ml-2 rounded-full px-2 py-0.5 text-xs font-medium">
              {pattern.frequency ?? 1}x
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
