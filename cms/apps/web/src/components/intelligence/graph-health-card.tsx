"use client";

import { Network } from "../icons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useGraphHealth } from "@/hooks/use-intelligence-stats";

export function GraphHealthCard() {
  const { data, isLoading } = useGraphHealth();

  if (isLoading) {
    return <Skeleton className="border-card-border h-24 rounded-lg border" />;
  }

  const healthy = data?.healthy ?? false;

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-6">
      <div className="flex items-center gap-2">
        <Network className="text-foreground-muted h-4 w-4" />
        <p className="text-foreground-muted text-sm font-medium">{"Knowledge Graph"}</p>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <div
          className={`h-3 w-3 rounded-full ${healthy ? "bg-status-success" : "bg-status-danger"}`}
        />
        <p
          className={`text-lg font-semibold ${
            healthy ? "text-status-success" : "text-status-danger"
          }`}
        >
          {healthy ? "Online" : "Offline"}
        </p>
      </div>
      <p className="text-foreground-muted mt-1 text-xs">
        {"Cognee knowledge graph connectivity status"}
      </p>
    </div>
  );
}
