"use client";

import { useState } from "react";
import { RefreshCw } from "../icons";
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

  const healthMap = new Map((health?.plugins ?? []).map((h) => [h.name, h]));

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
          <span className="bg-status-success/10 text-status-success rounded-full px-3 py-1 text-sm font-medium">
            {health.healthy} healthy
          </span>
          <span className="bg-status-warning/10 text-status-warning rounded-full px-3 py-1 text-sm font-medium">
            {health.degraded} degraded
          </span>
          <span className="bg-status-error/10 text-status-error rounded-full px-3 py-1 text-sm font-medium">
            {health.unhealthy} unhealthy
          </span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center justify-between">
        <div className="border-card-border bg-card-bg flex gap-1 rounded-lg border p-1">
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
          className="border-card-border text-foreground-muted hover:bg-surface-hover flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {/* Plugin List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="border-card-border bg-card-bg h-20 animate-pulse rounded-lg border"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-foreground-muted py-8 text-center">No plugins match this filter.</p>
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
