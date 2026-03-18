"use client";

import { Activity, Target, AlertTriangle, Clock } from "lucide-react";
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
            const rate = test.clients_requested > 0
              ? ((test.clients_completed ?? 0) / test.clients_requested) * 100
              : 0;
            return s + rate;
          }, 0) / tests.length,
        )
      : 0;

  // Find worst client (highest fail rate across all tests)
  const clientFailCounts: Record<string, { fails: number; total: number; name: string }> = {};
  for (const test of tests) {
    for (const s of (test.screenshots ?? [])) {
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
      <div className="rounded-lg border border-card-border bg-card-bg p-4">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-foreground-muted" />
          <span className="text-sm text-foreground-muted">{"Total Tests"}</span>
        </div>
        <p className="mt-2 text-2xl font-semibold text-foreground">{totalTests}</p>
      </div>

      <div className="rounded-lg border border-card-border bg-card-bg p-4">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-foreground-muted" />
          <span className="text-sm text-foreground-muted">{"Completion Rate"}</span>
        </div>
        <p className={`mt-2 text-2xl font-semibold ${completionColor}`}>{avgCompletion}%</p>
      </div>

      <div className="rounded-lg border border-card-border bg-card-bg p-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-foreground-muted" />
          <span className="text-sm text-foreground-muted">{"Most Problematic"}</span>
        </div>
        <p className="mt-2 text-lg font-semibold text-foreground">{worstName}</p>
        {worstRate > 0 && (
          <p className="text-xs text-status-danger">{worstRate}% {"fail rate"}</p>
        )}
      </div>

      <div className="rounded-lg border border-card-border bg-card-bg p-4">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-foreground-muted" />
          <span className="text-sm text-foreground-muted">{"Last Test"}</span>
        </div>
        <p className="mt-2 text-2xl font-semibold text-foreground">{lastDate}</p>
      </div>
    </div>
  );
}
