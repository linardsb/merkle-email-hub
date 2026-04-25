"use client";

import Link from "next/link";
import { MonitorSmartphone } from "../icons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useRenderingTests } from "@/hooks/use-renderings";

export function RenderingSummaryCard() {
  const { data, isLoading } = useRenderingTests({ pageSize: 10 });

  if (isLoading) {
    return <Skeleton className="border-card-border h-40 rounded-lg border" />;
  }

  const tests = data?.items ?? [];

  if (tests.length === 0) {
    return (
      <div className="border-card-border bg-card-bg rounded-lg border p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MonitorSmartphone className="text-foreground-muted h-5 w-5" />
            <h2 className="text-foreground text-lg font-semibold">{"Email Client Rendering"}</h2>
          </div>
          <span className="bg-surface-muted text-foreground-muted rounded-full px-2 py-0.5 text-xs font-medium">
            {"No Data"}
          </span>
        </div>
        <p className="text-foreground-muted mt-2 text-sm">
          {"Run your first cross-client rendering test to see how your emails look everywhere."}
        </p>
      </div>
    );
  }

  // Compute latest completion rate
  const latest = tests[0]!;
  const latestScore =
    latest.clients_requested > 0
      ? Math.round(((latest.clients_completed ?? 0) / latest.clients_requested) * 100)
      : 0;

  // Find most problematic clients
  const clientFails: Record<string, { fails: number; total: number; name: string }> = {};
  for (const test of tests) {
    for (const s of test.screenshots ?? []) {
      if (!clientFails[s.client_name]) {
        clientFails[s.client_name] = { fails: 0, total: 0, name: s.client_name };
      }
      const entry = clientFails[s.client_name]!;
      entry.total++;
      if (s.status === "failed") entry.fails++;
    }
  }
  const problematic = Object.values(clientFails)
    .map((v) => ({
      name: v.name,
      fail_rate: v.total > 0 ? Math.round((v.fails / v.total) * 100) : 0,
    }))
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
    <div className="border-card-border bg-card-bg rounded-lg border p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MonitorSmartphone className="text-foreground-muted h-5 w-5" />
          <h2 className="text-foreground text-lg font-semibold">{"Email Client Rendering"}</h2>
        </div>
        <Link href="/renderings" className="text-foreground-accent text-sm hover:underline">
          {"View All"}
        </Link>
      </div>

      <div className="mt-4 flex items-start gap-6">
        <div>
          <p className="text-foreground-muted text-sm">{"Latest Compatibility"}</p>
          <p className={`text-3xl font-bold ${scoreColor}`}>{latestScore}%</p>
        </div>

        {problematic.length > 0 && (
          <div className="flex-1">
            <p className="text-foreground-muted mb-2 text-sm">{"Most Problematic Clients"}</p>
            <div className="space-y-1.5">
              {problematic.map((client) => (
                <div key={client.name} className="flex items-center gap-2">
                  <span className="text-foreground w-24 truncate text-sm">{client.name}</span>
                  <div className="flex-1">
                    <div className="bg-surface-muted h-1.5 overflow-hidden rounded-full">
                      <div
                        className="bg-status-danger h-full rounded-full"
                        style={{ width: `${Math.min(client.fail_rate, 100)}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-foreground-muted w-10 text-right text-xs">
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
