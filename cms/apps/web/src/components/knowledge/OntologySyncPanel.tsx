"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { Database, ChevronDown, ChevronUp, Loader2, AlertTriangle, RefreshCw } from "../icons";
import { useOntologySyncStatus, useOntologySync } from "@/hooks/use-ontology";
import type { ChangelogEntry, SyncReportResponse } from "@/types/ontology";

function formatTimeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const LEVEL_STYLES: Record<string, string> = {
  full: "bg-badge-success-bg text-badge-success-text",
  partial: "bg-badge-warning-bg text-badge-warning-text",
  none: "bg-badge-danger-bg text-badge-danger-text",
};

function levelLabel(level: string): string {
  const labels: Record<string, string> = {
    full: "Full",
    partial: "Partial",
    none: "None",
  };
  return labels[level] ?? "Unknown";
}

function ChangelogRow({ entry }: { entry: ChangelogEntry }) {
  const newStyle = LEVEL_STYLES[entry.new_level] ?? LEVEL_STYLES.none;
  const oldStyle = entry.old_level ? (LEVEL_STYLES[entry.old_level] ?? LEVEL_STYLES.none) : "";

  return (
    <div className="flex items-center gap-2 rounded border border-border bg-card px-2.5 py-1.5 text-xs">
      <span className="font-mono text-foreground-muted">{entry.property_id}</span>
      <span className="text-foreground-muted">{entry.client_id}</span>
      <span className="ml-auto flex items-center gap-1">
        {entry.old_level && (
          <>
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${oldStyle}`}>
              {levelLabel(entry.old_level)}
            </span>
            <span className="text-foreground-muted">→</span>
          </>
        )}
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${newStyle}`}>
          {levelLabel(entry.new_level)}
        </span>
      </span>
    </div>
  );
}

function SyncResults({ report }: { report: SyncReportResponse }) {
  const [showChangelog, setShowChangelog] = useState(false);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-card px-2 py-0.5 font-medium text-foreground">
          {`${report.new_properties} new properties`}
        </span>
        <span className="rounded-full bg-card px-2 py-0.5 font-medium text-foreground">
          {`${report.updated_levels} updated levels`}
        </span>
        <span className="rounded-full bg-card px-2 py-0.5 font-medium text-foreground">
          {`${report.new_clients} new clients`}
        </span>
      </div>

      {report.dry_run && (
        <p className="text-[10px] text-foreground-muted">{"Dry run — no changes applied"}</p>
      )}

      {report.changelog.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowChangelog((v) => !v)}
            className="flex w-full items-center justify-between text-xs font-medium text-foreground-muted"
          >
            <span>{"Changelog"} ({report.changelog.length})</span>
            {showChangelog ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>
          {showChangelog && (
            <div className="mt-1.5 max-h-48 space-y-1 overflow-y-auto">
              {report.changelog.map((entry, i) => (
                <ChangelogRow
                  key={`${entry.property_id}-${entry.client_id}-${i}`}
                  entry={entry}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {report.changelog.length === 0 && (
        <p className="text-xs text-foreground-muted">{"No changes detected"}</p>
      )}

      {report.errors.length > 0 && (
        <div className="rounded border border-status-warning/30 bg-badge-warning-bg p-2 text-xs text-badge-warning-text">
          {report.errors.map((err, i) => (
            <p key={i}>{err}</p>
          ))}
        </div>
      )}
    </div>
  );
}

export function OntologySyncPanel() {
  const session = useSession();
  const isAdmin = session.data?.user?.role === "admin";

  const { data: status, isLoading: statusLoading } = useOntologySyncStatus();
  const { trigger: syncTrigger, data: syncReport, isMutating: isSyncing } = useOntologySync();

  const lastSyncText = status?.last_sync_at
    ? `Last synced ${formatTimeAgo(status.last_sync_at)}`
    : "Never synced";

  return (
    <div className="rounded-lg bg-surface-muted p-3">
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-foreground-muted" />
          <h3 className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
            {"Ontology Sync"}
          </h3>
        </div>
        {isAdmin && (
          <button
            type="button"
            disabled={isSyncing}
            onClick={() => syncTrigger({ dry_run: true })}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
          >
            {isSyncing ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                {"Syncing…"}
              </>
            ) : (
              <>
                <RefreshCw className="h-3 w-3" />
                {"Sync Now (Dry Run)"}
              </>
            )}
          </button>
        )}
      </div>

      {/* Status */}
      {statusLoading ? (
        <div className="flex items-center gap-2 text-xs text-foreground-muted">
          <Loader2 className="h-3 w-3 animate-spin" />
        </div>
      ) : status ? (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-card px-2 py-0.5 text-foreground-muted">
              {lastSyncText}
            </span>
            <span className="rounded-full bg-card px-2 py-0.5 font-medium text-foreground">
              {`${status.features_synced} features synced`}
            </span>
            {status.error_count > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-badge-danger-bg px-2 py-0.5 text-badge-danger-text">
                <AlertTriangle className="h-3 w-3" />
                {`${status.error_count} errors`}
              </span>
            )}
          </div>
          {status.last_commit_sha && (
            <p className="font-mono text-[10px] text-foreground-muted">
              {`Commit: ${status.last_commit_sha.slice(0, 8)}`}
            </p>
          )}
        </div>
      ) : null}

      {/* Sync report (after manual sync) */}
      {syncReport && (
        <div className="mt-3 border-t border-border pt-3">
          <p className="mb-2 text-xs font-medium text-status-success">{"Sync complete"}</p>
          <SyncResults report={syncReport} />
        </div>
      )}
    </div>
  );
}
