"use client";

import { useMemo } from "react";
import { Bot } from "../icons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useFailurePatterns } from "@/hooks/use-failure-patterns";

function severityColorClass(count: number, max: number): string {
  const ratio = max > 0 ? count / max : 0;
  if (ratio >= 0.6) return "bg-status-danger";
  if (ratio >= 0.3) return "bg-status-warning";
  return "bg-status-success";
}

export function AgentPerformanceChart() {
  const { data, isLoading } = useFailurePatterns({
    page: 1,
    pageSize: 100,
  });

  const agentStats = useMemo(() => {
    const patterns = data?.items ?? [];
    const counts: Record<string, number> = {};

    for (const p of patterns) {
      const name = p.agent_name;
      counts[name] = (counts[name] ?? 0) + 1;
    }

    return Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }, [data]);

  const maxCount = agentStats.length > 0 ? agentStats[0]!.count : 0;

  if (isLoading) {
    return <Skeleton className="border-card-border h-64 rounded-lg border" />;
  }

  if (agentStats.length === 0) {
    return (
      <div className="border-card-border bg-card-bg rounded-lg border p-6">
        <div className="flex items-center gap-2">
          <Bot className="text-foreground-muted h-5 w-5" />
          <h2 className="text-foreground text-lg font-semibold">{"Agent Performance"}</h2>
        </div>
        <p className="text-foreground-muted mt-2 text-sm">
          {"No agent performance data yet. Run blueprints to see agent metrics."}
        </p>
      </div>
    );
  }

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-6">
      <div className="flex items-center gap-2">
        <Bot className="text-foreground-muted h-5 w-5" />
        <h2 className="text-foreground text-lg font-semibold">{"Agent Performance"}</h2>
      </div>
      <p className="text-foreground-muted mt-1 text-sm">
        {"Failure pattern frequency per agent from blueprint runs"}
      </p>
      <div className="mt-4 space-y-3">
        {agentStats.map((agent) => {
          const pct = maxCount > 0 ? Math.round((agent.count / maxCount) * 100) : 0;
          return (
            <div key={agent.name}>
              <div className="flex items-center justify-between text-sm">
                <span className="text-foreground capitalize">{agent.name.replace(/_/g, " ")}</span>
                <span className="text-foreground-muted text-xs">
                  {agent.count} {"patterns"}
                </span>
              </div>
              <div className="bg-surface-muted mt-1 h-2 w-full rounded-full">
                <div
                  className={`h-2 rounded-full transition-all ${severityColorClass(agent.count, maxCount)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
