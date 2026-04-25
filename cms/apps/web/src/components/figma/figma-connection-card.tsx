"use client";

import { Figma, FolderOpen, RefreshCw, Trash2, Loader2 } from "../icons";
import { FigmaStatusBadge } from "./figma-status-badge";
import type { FigmaConnection } from "@/types/figma";

interface FigmaConnectionCardProps {
  connection: FigmaConnection;
  selected: boolean;
  syncing: boolean;
  onSelect: () => void;
  onSync: () => void;
  onDelete: () => void;
}

export function FigmaConnectionCard({
  connection,
  selected,
  syncing,
  onSelect,
  onSync,
  onDelete,
}: FigmaConnectionCardProps) {
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
      {/* Top row: icon + name + badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Figma className="text-foreground-muted h-5 w-5 shrink-0" />
          <div>
            <p className="text-foreground text-sm font-medium">{connection.name}</p>
            <p className="text-foreground-muted text-xs">
              {`Token ····${connection.access_token_last4}`}
            </p>
          </div>
        </div>
        <FigmaStatusBadge status={connection.status} />
      </div>

      {/* Meta row */}
      <div className="text-foreground-muted mt-3 flex items-center gap-4 text-xs">
        {connection.project_name && (
          <span className="flex items-center gap-1">
            <FolderOpen className="h-3.5 w-3.5" />
            {connection.project_name}
          </span>
        )}
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
          {syncing ? "Syncing\u2026" : "Sync Now"}
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
          Remove
        </button>
      </div>
    </div>
  );
}
