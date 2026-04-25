"use client";

import { AlertTriangle, Users, Target, Shield } from "../icons";
import type { FailurePatternStats } from "@/types/failure-patterns";

interface FailurePatternStatsCardsProps {
  stats: FailurePatternStats;
}

export function FailurePatternStatsCards({ stats }: FailurePatternStatsCardsProps) {
  const cards = [
    {
      label: "Total Patterns",
      value: String(stats.total_patterns),
      icon: AlertTriangle,
      colorClass: stats.total_patterns > 0 ? "text-status-warning" : "text-foreground",
    },
    {
      label: "Unique Agents",
      value: String(stats.unique_agents),
      icon: Users,
      colorClass: "text-foreground",
    },
    {
      label: "Unique Checks",
      value: String(stats.unique_checks),
      icon: Target,
      colorClass: "text-foreground",
    },
    {
      label: "Top Failing Check",
      value: stats.top_check ?? "-",
      icon: Shield,
      colorClass: stats.top_check ? "text-status-danger" : "text-foreground-muted",
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="border-card-border bg-card-bg rounded-lg border p-6">
          <div className="flex items-center gap-2">
            <card.icon className="text-foreground-muted h-4 w-4" />
            <p className="text-foreground-muted text-sm font-medium">{card.label}</p>
          </div>
          <p className={`mt-2 text-3xl font-semibold ${card.colorClass}`}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}
