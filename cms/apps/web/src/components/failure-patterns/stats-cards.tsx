"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle, Users, Target, Shield } from "lucide-react";
import type { FailurePatternStats } from "@/types/failure-patterns";

interface FailurePatternStatsCardsProps {
  stats: FailurePatternStats;
}

export function FailurePatternStatsCards({
  stats,
}: FailurePatternStatsCardsProps) {
  const t = useTranslations("failurePatterns");

  const cards = [
    {
      label: t("totalPatterns"),
      value: String(stats.total_patterns),
      icon: AlertTriangle,
      colorClass:
        stats.total_patterns > 0 ? "text-status-warning" : "text-foreground",
    },
    {
      label: t("uniqueAgents"),
      value: String(stats.unique_agents),
      icon: Users,
      colorClass: "text-foreground",
    },
    {
      label: t("uniqueChecks"),
      value: String(stats.unique_checks),
      icon: Target,
      colorClass: "text-foreground",
    },
    {
      label: t("topCheck"),
      value: stats.top_check ?? "-",
      icon: Shield,
      colorClass: stats.top_check
        ? "text-status-danger"
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
