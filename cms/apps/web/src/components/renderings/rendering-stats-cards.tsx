"use client";

import { Activity, Target, AlertTriangle, Clock } from "../icons";
import type { RenderingTest } from "@/types/rendering";

interface Props {
  tests: RenderingTest[];
}

export function RenderingStatsCards({ tests }: Props) {
  function formatRelativeDate(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return "Today";
    if (days === 1) return "Yesterday";
    return `${days}d ago`;
  }

  const totalTests = tests.length;

  // Avg completion rate
  const avgCompletion =
    tests.length > 0
      ? Math.round(
          tests.reduce((s, test) => {
            const rate =
              test.clients_requested > 0
                ? ((test.clients_completed ?? 0) / test.clients_requested) * 100
                : 0;
            return s + rate;
          }, 0) / tests.length,
        )
      : 0;

  // Find worst client (highest fail rate across all tests)
  const clientFailCounts: Record<string, { fails: number; total: number; name: string }> = {};
  for (const test of tests) {
    for (const s of test.screenshots ?? []) {
      if (!clientFailCounts[s.client_name]) {
        clientFailCounts[s.client_name] = { fails: 0, total: 0, name: s.client_name };
      }
      const entry = clientFailCounts[s.client_name]!;
      entry.total++;
      if (s.status === "failed") entry.fails++;
    }
  }
  const worstClient = Object.values(clientFailCounts).sort(
    (a, b) => b.fails / b.total - a.fails / a.total,
  )[0];
  const worstName = worstClient?.name ?? "—";
  const worstRate = worstClient ? Math.round((worstClient.fails / worstClient.total) * 100) : 0;

  const lastTest = tests[0];
  const lastDate = lastTest ? formatRelativeDate(lastTest.created_at) : "—";

  const completionColor =
    avgCompletion >= 80
      ? "text-status-success"
      : avgCompletion >= 60
        ? "text-status-warning"
        : "text-status-danger";

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className="border-card-border bg-card-bg rounded-lg border p-4">
        <div className="flex items-center gap-2">
          <Activity className="text-foreground-muted h-4 w-4" />
          <span className="text-foreground-muted text-sm">{"Total Tests"}</span>
        </div>
        <p className="text-foreground mt-2 text-2xl font-semibold">{totalTests}</p>
      </div>

      <div className="border-card-border bg-card-bg rounded-lg border p-4">
        <div className="flex items-center gap-2">
          <Target className="text-foreground-muted h-4 w-4" />
          <span className="text-foreground-muted text-sm">{"Completion Rate"}</span>
        </div>
        <p className={`mt-2 text-2xl font-semibold ${completionColor}`}>{avgCompletion}%</p>
      </div>

      <div className="border-card-border bg-card-bg rounded-lg border p-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="text-foreground-muted h-4 w-4" />
          <span className="text-foreground-muted text-sm">{"Most Problematic"}</span>
        </div>
        <p className="text-foreground mt-2 text-lg font-semibold">{worstName}</p>
        {worstRate > 0 && (
          <p className="text-status-danger text-xs">
            {worstRate}% {"fail rate"}
          </p>
        )}
      </div>

      <div className="border-card-border bg-card-bg rounded-lg border p-4">
        <div className="flex items-center gap-2">
          <Clock className="text-foreground-muted h-4 w-4" />
          <span className="text-foreground-muted text-sm">{"Last Test"}</span>
        </div>
        <p className="text-foreground mt-2 text-2xl font-semibold">{lastDate}</p>
      </div>
    </div>
  );
}
