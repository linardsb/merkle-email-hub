"use client";

import { Workflow, AlertTriangle, Users, ListChecks } from "../icons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useFailurePatternStats } from "@/hooks/use-failure-patterns";

export function BlueprintSuccessCard() {
  const { data: stats, isLoading } = useFailurePatternStats();

  if (isLoading) {
    return <Skeleton className="border-card-border h-40 rounded-lg border" />;
  }

  const totalPatterns = stats?.total_patterns ?? 0;
  const uniqueAgents = stats?.unique_agents ?? 0;
  const uniqueChecks = stats?.unique_checks ?? 0;
  const topCheck = stats?.top_check?.replace(/_/g, " ") ?? "—";

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-6">
      <div className="flex items-center gap-2">
        <Workflow className="text-foreground-muted h-5 w-5" />
        <h2 className="text-foreground text-lg font-semibold">{"Blueprint Health"}</h2>
      </div>
      <p className="text-foreground-muted mt-1 text-sm">
        {"Failure pattern summary from blueprint pipeline runs"}
      </p>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="text-status-warning h-4 w-4" />
          <div>
            <p className="text-foreground-muted text-xs">{"Patterns"}</p>
            <p className="text-foreground text-lg font-semibold">{totalPatterns}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Users className="text-foreground-muted h-4 w-4" />
          <div>
            <p className="text-foreground-muted text-xs">{"Agents"}</p>
            <p className="text-foreground text-lg font-semibold">{uniqueAgents}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ListChecks className="text-foreground-muted h-4 w-4" />
          <div>
            <p className="text-foreground-muted text-xs">{"Checks"}</p>
            <p className="text-foreground text-lg font-semibold">{uniqueChecks}</p>
          </div>
        </div>
        <div>
          <p className="text-foreground-muted text-xs">{"Top Failing Check"}</p>
          <p className="text-foreground text-sm font-medium capitalize">{topCheck}</p>
        </div>
      </div>
    </div>
  );
}
