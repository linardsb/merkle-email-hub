"use client";

import { Activity, Target, CheckCircle2, ShieldAlert } from "../icons";
import type { QADashboardMetrics } from "@/types/qa";

interface ScoreOverviewCardsProps {
  metrics: QADashboardMetrics;
}

export function ScoreOverviewCards({ metrics }: ScoreOverviewCardsProps) {
  const cards = [
    {
      label: "Total QA Runs",
      value: String(metrics.totalRuns),
      icon: Activity,
      colorClass: "text-foreground",
    },
    {
      label: "Average Score",
      value: `${Math.round(metrics.avgScore * 100)}%`,
      icon: Target,
      colorClass: "text-foreground",
    },
    {
      label: "Pass Rate",
      value: `${Math.round(metrics.passRate * 100)}%`,
      icon: CheckCircle2,
      colorClass: metrics.passRate >= 0.8 ? "text-status-success" : "text-status-danger",
    },
    {
      label: "Overrides",
      value: String(metrics.overrideCount),
      icon: ShieldAlert,
      colorClass: metrics.overrideCount > 0 ? "text-status-warning" : "text-foreground-muted",
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
