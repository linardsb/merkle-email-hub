"use client";

import { useTranslations } from "next-intl";
import type { QADashboardMetrics } from "@/types/qa";

interface ScoreTrendBarsProps {
  scoreTrend: QADashboardMetrics["scoreTrend"];
}

export function ScoreTrendBars({ scoreTrend }: ScoreTrendBarsProps) {
  const t = useTranslations("intelligence");

  if (scoreTrend.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-foreground-muted">
        {t("noResultsDescription")}
      </p>
    );
  }

  const first = scoreTrend[0]!;
  const last = scoreTrend[scoreTrend.length - 1]!;
  const dateFmt: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };

  return (
    <div>
      <div className="flex items-end gap-1" style={{ height: "10rem" }}>
        {scoreTrend.map((point, i) => {
          const pct = Math.round(point.score * 100);
          const dateStr = new Date(point.date).toLocaleDateString(
            undefined,
            dateFmt
          );
          return (
            <div
              key={i}
              className={`flex-1 rounded-t transition-all ${
                point.passed ? "bg-status-success" : "bg-status-danger"
              }`}
              style={{
                height: `${pct}%`,
                minHeight: point.score > 0 ? "4px" : "0",
              }}
              title={`${dateStr}: ${pct}%`}
            />
          );
        })}
      </div>
      <div className="mt-2 flex justify-between text-xs text-foreground-muted">
        <span>
          {new Date(first.date).toLocaleDateString(undefined, dateFmt)}
        </span>
        <span>
          {new Date(last.date).toLocaleDateString(undefined, dateFmt)}
        </span>
      </div>
    </div>
  );
}
