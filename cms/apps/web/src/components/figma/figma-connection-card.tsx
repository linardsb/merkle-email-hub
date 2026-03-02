"use client";

import { useTranslations } from "next-intl";
import { Figma, FolderOpen, RefreshCw, Trash2, Loader2 } from "lucide-react";
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
  const t = useTranslations("figma");

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
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border-2 bg-card-bg p-4 text-left transition-colors ${
        selected
          ? "border-interactive ring-1 ring-interactive"
          : "border-card-border hover:bg-surface-hover"
      }`}
    >
      {/* Top row: icon + name + badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Figma className="h-5 w-5 shrink-0 text-foreground-muted" />
          <div>
            <p className="text-sm font-medium text-foreground">
              {connection.name}
            </p>
            <p className="text-xs text-foreground-muted">
              {t("tokenEnding", { last4: connection.access_token_last4 })}
            </p>
          </div>
        </div>
        <FigmaStatusBadge status={connection.status} />
      </div>

      {/* Meta row */}
      <div className="mt-3 flex items-center gap-4 text-xs text-foreground-muted">
        {connection.project_name && (
          <span className="flex items-center gap-1">
            <FolderOpen className="h-3.5 w-3.5" />
            {connection.project_name}
          </span>
        )}
        {lastSynced && (
          <span>{t("lastSynced", { date: lastSynced })}</span>
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
          {syncing ? t("syncing") : t("syncNow")}
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
          {t("remove")}
        </button>
      </div>
    </button>
  );
}
