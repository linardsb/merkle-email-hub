"use client";

import { FolderOpen, RefreshCw, Trash2, Loader2, Download, Puzzle, KeyRound } from "lucide-react";
import { DesignStatusBadge } from "./design-status-badge";
import { ProviderIcon } from "./provider-icon";
import type { DesignConnection } from "@/types/design-sync";

const PROVIDER_LABELS: Record<string, string> = {
  figma: "Figma",
  sketch: "Sketch",
  canva: "Canva",
};

interface ProjectOption {
  id: number;
  name: string;
}

interface DesignConnectionCardProps {
  connection: DesignConnection;
  selected: boolean;
  syncing: boolean;
  onSelect: () => void;
  onSync: () => void;
  onDelete: () => void;
  onImport: () => void;
  onExtractComponents: () => void;
  onRefreshToken?: () => void;
  onLinkProject?: (projectId: number | null) => void;
  projects?: ProjectOption[];
}

export function DesignConnectionCard({
  connection,
  selected,
  syncing,
  onSelect,
  onSync,
  onDelete,
  onImport,
  onExtractComponents,
  onRefreshToken,
  onLinkProject,
  projects,
}: DesignConnectionCardProps) {
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
      {/* Top row: icon + name + badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <ProviderIcon provider={connection.provider} className="h-5 w-5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-foreground">
              {connection.name}
            </p>
            <p className="text-xs text-foreground-muted">
              {PROVIDER_LABELS[connection.provider] ?? connection.provider}
              {" · "}
              {`Token ····${connection.access_token_last4}`}
            </p>
          </div>
        </div>
        <DesignStatusBadge status={connection.status} />
      </div>

      {/* Meta row */}
      <div className="mt-3 flex items-center gap-4 text-xs text-foreground-muted">
        {connection.project_id && connection.project_name ? (
          <span className="flex items-center gap-1">
            <FolderOpen className="h-3.5 w-3.5" />
            {connection.project_name}
            {onLinkProject && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onLinkProject(null);
                }}
                className="ml-1 text-foreground-muted hover:text-foreground"
                title="Unlink project"
              >
                {"×"}
              </button>
            )}
          </span>
        ) : onLinkProject && projects && projects.length > 0 ? (
          <span className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
            <FolderOpen className="h-3.5 w-3.5 text-status-warning" />
            <select
              value=""
              onChange={(e) => {
                if (e.target.value) onLinkProject(Number(e.target.value));
              }}
              className="rounded border border-border bg-card-bg px-1.5 py-0.5 text-xs text-foreground"
            >
              <option value="">{"Link to project…"}</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </span>
        ) : null}
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
        {onRefreshToken && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRefreshToken();
            }}
            className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover"
          >
            <KeyRound className="h-3.5 w-3.5" />
            {"Refresh Token"}
          </button>
        )}
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

        {connection.status === "connected" && (
          <>
            <div className="mx-1 h-4 w-px bg-card-border" />
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onImport();
              }}
              className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover"
            >
              <Download className="h-3.5 w-3.5" />
              {"Import Design"}
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onExtractComponents();
              }}
              className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover"
            >
              <Puzzle className="h-3.5 w-3.5" />
              {"Extract Components"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
