"use client";

import { FolderOpen, RefreshCw, Trash2, Loader2 } from "../icons";
import { BriefStatusBadge } from "./brief-status-badge";
import type { BriefConnection } from "@/types/briefs";

const PLATFORM_LABELS: Record<string, string> = {
  jira: "Jira",
  asana: "Asana",
  monday: "Monday.com",
  clickup: "ClickUp",
  trello: "Trello",
  notion: "Notion",
  wrike: "Wrike",
  basecamp: "Basecamp",
};

interface BriefConnectionCardProps {
  connection: BriefConnection;
  selected: boolean;
  syncing: boolean;
  onSelect: () => void;
  onSync: () => void;
  onDelete: () => void;
}

export function BriefConnectionCard({
  connection,
  selected,
  syncing,
  onSelect,
  onSync,
  onDelete,
}: BriefConnectionCardProps) {
  const lastSynced = connection.last_synced_at
    ? new Date(connection.last_synced_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className={`bg-card-bg w-full cursor-pointer rounded-lg border-2 p-4 text-left transition-colors ${
        selected
          ? "border-interactive ring-interactive ring-1"
          : "border-card-border hover:bg-surface-hover"
      }`}
    >
      {/* Top row: platform + name + badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="text-foreground-muted inline-flex h-5 w-5 shrink-0 items-center justify-center rounded text-xs font-bold">
            {PLATFORM_LABELS[connection.platform]?.[0] ?? "?"}
          </span>
          <div>
            <p className="text-foreground text-sm font-medium">{connection.name}</p>
            <p className="text-foreground-muted text-xs">
              {PLATFORM_LABELS[connection.platform]} &middot;{" "}
              {`Key ····${connection.credential_last4}`}
            </p>
          </div>
        </div>
        <BriefStatusBadge status={connection.status} />
      </div>

      {/* Meta row */}
      <div className="text-foreground-muted mt-3 flex items-center gap-4 text-xs">
        {connection.project_name && (
          <span className="flex items-center gap-1">
            <FolderOpen className="h-3.5 w-3.5" />
            {connection.project_name}
          </span>
        )}
        {connection.items_count > 0 && <span>{`${connection.items_count} briefs`}</span>}
        {lastSynced && <span>{`Synced ${lastSynced}`}</span>}
      </div>

      {/* Actions */}
      <div className="border-card-border mt-3 flex items-center gap-2 border-t pt-3">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSync();
          }}
          disabled={syncing}
          className="border-border text-foreground hover:bg-surface-hover flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
        >
          {syncing ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          {syncing ? "Syncing…" : "Sync Now"}
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="border-border text-status-danger hover:bg-surface-hover flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {"Remove"}
        </button>
      </div>
    </div>
  );
}
