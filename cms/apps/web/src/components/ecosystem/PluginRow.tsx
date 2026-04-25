"use client";

import { useState } from "react";
import { RotateCcw } from "../icons";
import { usePluginEnable, usePluginDisable, usePluginRestart } from "@/hooks/use-plugins";
import type { PluginInfo, PluginHealth } from "@/types/plugins";
import { useSession } from "next-auth/react";

const STATUS_STYLES: Record<string, { dot: string; label: string }> = {
  active: { dot: "bg-status-success", label: "Active" },
  degraded: { dot: "bg-status-warning", label: "Degraded" },
  error: { dot: "bg-status-error", label: "Error" },
  disabled: { dot: "bg-foreground-muted", label: "Disabled" },
};

interface Props {
  plugin: PluginInfo;
  health: PluginHealth | null;
  onMutated: () => void;
}

export function PluginRow({ plugin, health, onMutated }: Props) {
  const session = useSession();
  const isAdmin = session.data?.user?.role === "admin";

  const { trigger: enable, isMutating: enabling } = usePluginEnable(plugin.name);
  const { trigger: disable, isMutating: disabling } = usePluginDisable(plugin.name);
  const { trigger: restart, isMutating: restarting } = usePluginRestart(plugin.name);
  const [error, setError] = useState<string | null>(null);

  const isBusy = enabling || disabling || restarting;
  const style = STATUS_STYLES[plugin.status] ?? { dot: "bg-foreground-muted", label: "Unknown" };

  async function handleToggle() {
    setError(null);
    try {
      if (plugin.status === "disabled") {
        await enable();
      } else {
        await disable();
      }
      onMutated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    }
  }

  async function handleRestart() {
    setError(null);
    try {
      await restart();
      onMutated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Restart failed");
    }
  }

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`inline-block h-2.5 w-2.5 rounded-full ${style.dot}`} />
            <span className="font-medium">{plugin.name}</span>
            <span className="text-foreground-muted text-xs">v{plugin.version}</span>
            <span className="border-card-border text-foreground-muted rounded border px-1.5 py-0.5 text-xs">
              {plugin.plugin_type}
            </span>
          </div>
          <p className="text-foreground-muted mt-1 text-sm">{plugin.description}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {plugin.tags.map((tag) => (
              <span
                key={tag}
                className="bg-surface-hover text-foreground-muted rounded-full px-2 py-0.5 text-xs"
              >
                {tag}
              </span>
            ))}
            <span className="text-foreground-muted text-xs">by {plugin.author}</span>
          </div>
          {health && health.latency_ms > 0 && (
            <p className="text-foreground-muted mt-1 text-xs">
              Health: {health.status} · {health.latency_ms}ms
              {health.message && ` · ${health.message}`}
            </p>
          )}
          {plugin.error && <p className="text-status-error mt-1 text-xs">{plugin.error}</p>}
          {error && <p className="text-status-error mt-1 text-xs">{error}</p>}
        </div>

        {isAdmin && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleToggle}
              disabled={isBusy}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50 ${
                plugin.status === "disabled"
                  ? "bg-status-success/10 text-status-success hover:bg-status-success/20"
                  : "bg-surface-hover text-foreground-muted hover:text-foreground"
              }`}
            >
              {plugin.status === "disabled" ? "Enable" : "Disable"}
            </button>
            {plugin.status !== "disabled" && (
              <button
                onClick={handleRestart}
                disabled={isBusy}
                className="border-card-border text-foreground-muted hover:bg-surface-hover rounded-md border p-1.5 disabled:opacity-50"
                title="Restart plugin"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
