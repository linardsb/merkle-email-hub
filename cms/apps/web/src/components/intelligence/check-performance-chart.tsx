"use client";

import { useMemo } from "react";
import type { QADashboardMetrics } from "@/types/qa";

interface CheckPerformanceChartProps {
  checkAverages: QADashboardMetrics["checkAverages"];
}

function scoreColorClass(score: number): string {
  if (score >= 0.8) return "bg-status-success";
  if (score >= 0.5) return "bg-status-warning";
  return "bg-status-danger";
}

const QA_CHECK_LABELS: Record<string, string> = {
  html_validation: "HTML Validation",
  css_support: "CSS Support",
  file_size: "File Size",
  link_validation: "Link Validation",
  spam_score: "Spam Score",
  dark_mode: "Dark Mode",
  accessibility: "Accessibility",
  fallback: "Fallback Support",
  image_optimization: "Image Optimization",
  brand_compliance: "Brand Compliance",
};

export function CheckPerformanceChart({ checkAverages }: CheckPerformanceChartProps) {
  const sorted = useMemo(
    () => [...checkAverages].sort((a, b) => a.avgScore - b.avgScore),
    [checkAverages],
  );

  return (
    <div className="space-y-3">
      {sorted.map((check) => {
        const pct = Math.round(check.avgScore * 100);
        const passRatePct = Math.round(check.passRate * 100);
        const label = QA_CHECK_LABELS[check.checkName] ?? check.checkName.replace(/_/g, " ");

        return (
          <div key={check.checkName}>
            <div className="flex items-center justify-between text-sm">
              <span className="text-foreground">{label}</span>
              <div className="flex items-center gap-3">
                <span className="text-foreground-muted text-xs">{passRatePct}% pass</span>
                <span className="text-foreground w-10 text-right font-medium">{pct}%</span>
              </div>
            </div>
            <div className="bg-surface-muted mt-1 h-2 w-full rounded-full">
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
