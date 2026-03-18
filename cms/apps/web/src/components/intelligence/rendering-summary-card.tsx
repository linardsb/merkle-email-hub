"use client";

import Link from "next/link";
import { MonitorSmartphone } from "lucide-react";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useRenderingTests } from "@/hooks/use-renderings";

export function RenderingSummaryCard() {
  const { data, isLoading } = useRenderingTests({ pageSize: 10 });

  if (isLoading) {
    return <Skeleton className="h-40 rounded-lg border border-card-border" />;
  }

  const tests = data?.items ?? [];

  if (tests.length === 0) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MonitorSmartphone className="h-5 w-5 text-foreground-muted" />
            <h2 className="text-lg font-semibold text-foreground">{"Email Client Rendering"}</h2>
          </div>
          <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs font-medium text-foreground-muted">
            {"No Data"}
          </span>
        </div>
        <p className="mt-2 text-sm text-foreground-muted">{"Run your first cross-client rendering test to see how your emails look everywhere."}</p>
      </div>
    );
  }

  // Compute latest completion rate
  const latest = tests[0]!;
  const latestScore = latest.clients_requested > 0
    ? Math.round(((latest.clients_completed ?? 0) / latest.clients_requested) * 100)
    : 0;

  // Find most problematic clients
  const clientFails: Record<string, { fails: number; total: number; name: string }> = {};
  for (const test of tests) {
    for (const s of (test.screenshots ?? [])) {
      if (!clientFails[s.client_name]) {
        clientFails[s.client_name] = { fails: 0, total: 0, name: s.client_name };
      }
      const entry = clientFails[s.client_name]!;
      entry.total++;
      if (s.status === "failed") entry.fails++;
    }
  }
  const problematic = Object.values(clientFails)
    .map((v) => ({ name: v.name, fail_rate: v.total > 0 ? Math.round((v.fails / v.total) * 100) : 0 }))
    .filter((c) => c.fail_rate > 0)
    .sort((a, b) => b.fail_rate - a.fail_rate)
    .slice(0, 3);

  const scoreColor =
    latestScore >= 80
      ? "text-status-success"
      : latestScore >= 60
        ? "text-status-warning"
        : "text-status-danger";

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MonitorSmartphone className="h-5 w-5 text-foreground-muted" />
          <h2 className="text-lg font-semibold text-foreground">{"Email Client Rendering"}</h2>
        </div>
        <Link
          href="/renderings"
          className="text-sm text-foreground-accent hover:underline"
        >
          {"View All"}
        </Link>
      </div>

      <div className="mt-4 flex items-start gap-6">
        <div>
          <p className="text-sm text-foreground-muted">{"Latest Compatibility"}</p>
          <p className={`text-3xl font-bold ${scoreColor}`}>{latestScore}%</p>
        </div>

        {problematic.length > 0 && (
          <div className="flex-1">
            <p className="mb-2 text-sm text-foreground-muted">{"Most Problematic Clients"}</p>
            <div className="space-y-1.5">
              {problematic.map((client) => (
                <div key={client.name} className="flex items-center gap-2">
                  <span className="w-24 truncate text-sm text-foreground">
                    {client.name}
                  </span>
                  <div className="flex-1">
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface-muted">
                      <div
                        className="h-full rounded-full bg-status-danger"
                        style={{ width: `${Math.min(client.fail_rate, 100)}%` }}
                      />
                    </div>
                  </div>
                  <span className="w-10 text-right text-xs text-foreground-muted">
                    {client.fail_rate}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
