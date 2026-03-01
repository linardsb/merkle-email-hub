"use client";

import { useMemo } from "react";
import { useQAResults } from "./use-qa";
import type { QADashboardMetrics, QAResultResponse } from "@/types/qa";

const CHECK_NAMES = [
  "html_validation",
  "css_support",
  "file_size",
  "link_validation",
  "spam_score",
  "dark_mode",
  "accessibility",
  "fallback",
  "image_optimization",
  "brand_compliance",
] as const;

function computeMetrics(items: QAResultResponse[]): QADashboardMetrics {
  const totalRuns = items.length;

  if (totalRuns === 0) {
    return {
      totalRuns: 0,
      avgScore: 0,
      passRate: 0,
      overrideCount: 0,
      checkAverages: CHECK_NAMES.map((name) => ({
        checkName: name,
        avgScore: 0,
        passRate: 0,
      })),
      scoreTrend: [],
    };
  }

  const avgScore =
    items.reduce((sum, r) => sum + r.overall_score, 0) / totalRuns;
  const passRate = items.filter((r) => r.passed).length / totalRuns;
  const overrideCount = items.filter((r) => r.override).length;

  const checkAverages = CHECK_NAMES.map((checkName) => {
    let scoreSum = 0;
    let passCount = 0;
    let count = 0;

    for (const result of items) {
      const check = result.checks.find((c) => c.check_name === checkName);
      if (check) {
        scoreSum += check.score;
        if (check.passed) passCount++;
        count++;
      }
    }

    return {
      checkName,
      avgScore: count > 0 ? scoreSum / count : 0,
      passRate: count > 0 ? passCount / count : 0,
    };
  });

  const sorted = [...items].sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  const scoreTrend = sorted.slice(-20).map((r) => ({
    score: r.overall_score,
    passed: r.passed,
    date: r.created_at,
  }));

  return {
    totalRuns,
    avgScore,
    passRate,
    overrideCount,
    checkAverages,
    scoreTrend,
  };
}

export function useQADashboard() {
  const { data, isLoading, error } = useQAResults({ page: 1, pageSize: 50 });

  const metrics = useMemo(
    () => computeMetrics(data?.items ?? []),
    [data?.items]
  );

  return {
    metrics,
    total: data?.total ?? 0,
    isLoading,
    error,
  };
}
