"use client";

import { FolderOpen, RefreshCw, Trash2, Loader2 } from "lucide-react";
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
      className={`w-full cursor-pointer rounded-lg border-2 bg-card-bg p-4 text-left transition-colors ${
        selected
          ? "border-interactive ring-1 ring-interactive"
          : "border-card-border hover:bg-surface-hover"
      }`}
    >
      {/* Top row: platform + name + badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded text-xs font-bold text-foreground-muted">
            {PLATFORM_LABELS[connection.platform]?.[0] ?? "?"}
          </span>
          <div>
            <p className="text-sm font-medium text-foreground">
              {connection.name}
            </p>
            <p className="text-xs text-foreground-muted">
              {PLATFORM_LABELS[connection.platform]} &middot; {`Key ····${connection.credential_last4}`}
            </p>
          </div>
        </div>
        <BriefStatusBadge status={connection.status} />
      </div>

      {/* Meta row */}
      <div className="mt-3 flex items-center gap-4 text-xs text-foreground-muted">
        {connection.project_name && (
          <span className="flex items-center gap-1">
            <FolderOpen className="h-3.5 w-3.5" />
            {connection.project_name}
          </span>
        )}
        {connection.items_count > 0 && (
          <span>{`${connection.items_count} briefs`}</span>
        )}
        {lastSynced && (
          <span>{`Synced ${lastSynced}`}</span>
        )}
      </div>

      {/* Actions */}
      <div className="mt-3 flex items-center gap-2 border-t border-card-border pt-3">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSync();
          }}
          disabled={syncing}
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
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
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-status-danger transition-colors hover:bg-surface-hover"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {"Remove"}
        </button>
      </div>
    </div>
  );
}
