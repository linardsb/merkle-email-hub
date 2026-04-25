"use client";

import type { QADashboardMetrics } from "@/types/qa";

interface ScoreTrendBarsProps {
  scoreTrend: QADashboardMetrics["scoreTrend"];
}

export function ScoreTrendBars({ scoreTrend }: ScoreTrendBarsProps) {
  if (scoreTrend.length === 0) {
    return (
      <p className="text-foreground-muted py-8 text-center text-sm">
        {"Run QA checks on your templates to see intelligence data here."}
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
          const dateStr = new Date(point.date).toLocaleDateString(undefined, dateFmt);
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
      <div className="text-foreground-muted mt-2 flex justify-between text-xs">
        <span>{new Date(first.date).toLocaleDateString(undefined, dateFmt)}</span>
        <span>{new Date(last.date).toLocaleDateString(undefined, dateFmt)}</span>
      </div>
    </div>
  );
}
