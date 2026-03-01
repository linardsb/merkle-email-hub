"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import type { QADashboardMetrics } from "@/types/qa";

interface CheckPerformanceChartProps {
  checkAverages: QADashboardMetrics["checkAverages"];
}

function scoreColorClass(score: number): string {
  if (score >= 0.8) return "bg-status-success";
  if (score >= 0.5) return "bg-status-warning";
  return "bg-status-danger";
}

export function CheckPerformanceChart({
  checkAverages,
}: CheckPerformanceChartProps) {
  const tQa = useTranslations("qa");

  const sorted = useMemo(
    () => [...checkAverages].sort((a, b) => a.avgScore - b.avgScore),
    [checkAverages]
  );

  return (
    <div className="space-y-3">
      {sorted.map((check) => {
        const pct = Math.round(check.avgScore * 100);
        const passRatePct = Math.round(check.passRate * 100);
        const label =
          tQa.has(`check_${check.checkName}`)
            ? tQa(`check_${check.checkName}`)
            : check.checkName.replace(/_/g, " ");

        return (
          <div key={check.checkName}>
            <div className="flex items-center justify-between text-sm">
              <span className="text-foreground">{label}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-foreground-muted">
                  {passRatePct}% pass
                </span>
                <span className="w-10 text-right font-medium text-foreground">
                  {pct}%
                </span>
              </div>
            </div>
            <div className="mt-1 h-2 w-full rounded-full bg-surface-muted">
              <div
                className={`h-2 rounded-full transition-all ${scoreColorClass(check.avgScore)}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
