"use client";

import { useTranslations } from "next-intl";
import { Activity, Target, AlertTriangle, Clock } from "lucide-react";
import type { RenderingTest } from "@/types/rendering";

interface Props {
  tests: RenderingTest[];
}

export function RenderingStatsCards({ tests }: Props) {
  const t = useTranslations("renderings");

  function formatRelativeDate(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return t("today");
    if (days === 1) return t("yesterday");
    return t("daysAgo", { count: days });
  }

  const totalTests = tests.length;

  const avgCompat =
    tests.length > 0
      ? Math.round(tests.reduce((s, t) => s + t.compatibility_score, 0) / tests.length)
      : 0;

  // Find worst client (highest fail rate across all tests)
  const clientFailCounts: Record<string, { fails: number; total: number; name: string }> = {};
  for (const test of tests) {
    for (const r of test.results) {
      if (!clientFailCounts[r.client_id]) {
        clientFailCounts[r.client_id] = { fails: 0, total: 0, name: r.client_id };
      }
      const entry = clientFailCounts[r.client_id]!;
      entry.total++;
      if (r.status === "fail") entry.fails++;
    }
  }
  const worstClient = Object.values(clientFailCounts).sort(
    (a, b) => b.fails / b.total - a.fails / a.total,
  )[0];
  const worstName = worstClient?.name.replace(/_/g, " ") ?? "—";
  const worstRate = worstClient ? Math.round((worstClient.fails / worstClient.total) * 100) : 0;

  const lastTest = tests[0];
  const lastDate = lastTest ? formatRelativeDate(lastTest.created_at) : "—";

  const compatColor =
    avgCompat >= 80
      ? "text-status-success"
      : avgCompat >= 60
        ? "text-status-warning"
        : "text-status-danger";

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className="rounded-lg border border-card-border bg-card-bg p-4">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-foreground-muted" />
          <span className="text-sm text-foreground-muted">{t("totalTests")}</span>
        </div>
        <p className="mt-2 text-2xl font-semibold text-foreground">{totalTests}</p>
      </div>

      <div className="rounded-lg border border-card-border bg-card-bg p-4">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-foreground-muted" />
          <span className="text-sm text-foreground-muted">{t("avgCompatibility")}</span>
        </div>
        <p className={`mt-2 text-2xl font-semibold ${compatColor}`}>{avgCompat}%</p>
      </div>

      <div className="rounded-lg border border-card-border bg-card-bg p-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-foreground-muted" />
          <span className="text-sm text-foreground-muted">{t("mostProblematic")}</span>
        </div>
        <p className="mt-2 text-lg font-semibold capitalize text-foreground">{worstName}</p>
        {worstRate > 0 && (
          <p className="text-xs text-status-danger">{worstRate}% {t("failRate")}</p>
        )}
      </div>

      <div className="rounded-lg border border-card-border bg-card-bg p-4">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-foreground-muted" />
          <span className="text-sm text-foreground-muted">{t("lastTestDate")}</span>
        </div>
        <p className="mt-2 text-2xl font-semibold text-foreground">{lastDate}</p>
      </div>
    </div>
  );
}
