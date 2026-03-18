"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { usePlugins, usePluginHealthSummary } from "@/hooks/use-plugins";
import { PluginRow } from "./PluginRow";
import type { PluginStatus } from "@/types/plugins";

type StatusFilter = "all" | PluginStatus;

export function PluginManagerPanel() {
  const { data: pluginList, isLoading, mutate } = usePlugins();
  const { data: health } = usePluginHealthSummary();
  const [filter, setFilter] = useState<StatusFilter>("all");

  const plugins = pluginList?.plugins ?? [];
  const filtered = filter === "all" ? plugins : plugins.filter((p) => p.status === filter);

  const healthMap = new Map(
    (health?.plugins ?? []).map((h) => [h.name, h]),
  );

  const filters: { label: string; value: StatusFilter }[] = [
    { label: "All", value: "all" },
    { label: "Active", value: "active" },
    { label: "Degraded", value: "degraded" },
    { label: "Disabled", value: "disabled" },
    { label: "Error", value: "error" },
  ];

  return (
    <div className="space-y-6">
      {/* Health Summary */}
      {health && (
        <div className="flex gap-3">
          <span className="rounded-full bg-status-success/10 px-3 py-1 text-sm font-medium text-status-success">
            {health.healthy} healthy
          </span>
          <span className="rounded-full bg-status-warning/10 px-3 py-1 text-sm font-medium text-status-warning">
            {health.degraded} degraded
          </span>
          <span className="rounded-full bg-status-error/10 px-3 py-1 text-sm font-medium text-status-error">
            {health.unhealthy} unhealthy
          </span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg border border-card-border bg-card-bg p-1">
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                filter === f.value
                  ? "bg-interactive text-foreground-inverse"
                  : "text-foreground-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => mutate()}
          className="flex items-center gap-1.5 rounded-md border border-card-border px-3 py-1.5 text-sm text-foreground-muted hover:bg-surface-hover"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {/* Plugin List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg border border-card-border bg-card-bg" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="py-8 text-center text-foreground-muted">No plugins match this filter.</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((plugin) => (
            <PluginRow
              key={plugin.name}
              plugin={plugin}
              health={healthMap.get(plugin.name) ?? null}
              onMutated={() => mutate()}
            />
          ))}
        </div>
      )}
    </div>
  );
}
