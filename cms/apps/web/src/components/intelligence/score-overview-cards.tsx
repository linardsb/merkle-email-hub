"use client";

import { useTranslations } from "next-intl";
import { Activity, Target, CheckCircle2, ShieldAlert } from "lucide-react";
import type { QADashboardMetrics } from "@/types/qa";

interface ScoreOverviewCardsProps {
  metrics: QADashboardMetrics;
}

export function ScoreOverviewCards({ metrics }: ScoreOverviewCardsProps) {
  const t = useTranslations("intelligence");

  const cards = [
    {
      label: t("totalRuns"),
      value: String(metrics.totalRuns),
      icon: Activity,
      colorClass: "text-foreground",
    },
    {
      label: t("avgScore"),
      value: `${Math.round(metrics.avgScore * 100)}%`,
      icon: Target,
      colorClass: "text-foreground",
    },
    {
      label: t("passRate"),
      value: `${Math.round(metrics.passRate * 100)}%`,
      icon: CheckCircle2,
      colorClass:
        metrics.passRate >= 0.8 ? "text-status-success" : "text-status-danger",
    },
    {
      label: t("overrides"),
      value: String(metrics.overrideCount),
      icon: ShieldAlert,
      colorClass:
        metrics.overrideCount > 0
          ? "text-status-warning"
          : "text-foreground-muted",
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-lg border border-card-border bg-card-bg p-6"
        >
          <div className="flex items-center gap-2">
            <card.icon className="h-4 w-4 text-foreground-muted" />
            <p className="text-sm font-medium text-foreground-muted">
              {card.label}
            </p>
          </div>
          <p className={`mt-2 text-3xl font-semibold ${card.colorClass}`}>
            {card.value}
          </p>
        </div>
      ))}
    </div>
  );
}
