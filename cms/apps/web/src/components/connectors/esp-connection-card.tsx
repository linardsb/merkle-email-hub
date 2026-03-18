"use client";

import { Trash2 } from "lucide-react";
import { ESP_LABELS } from "@/types/esp-sync";
import type { ESPConnectionResponse } from "@/types/esp-sync";

interface ESPConnectionCardProps {
  connection: ESPConnectionResponse;
  selected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

export function ESPConnectionCard({
  connection,
  selected,
  onSelect,
  onDelete,
}: ESPConnectionCardProps) {
  const lastSynced = connection.last_synced_at
    ? new Date(connection.last_synced_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  const espInfo = ESP_LABELS[connection.esp_type] ?? {
    label: connection.esp_type,
    color: "bg-surface-muted text-foreground-muted",
  };

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
      {/* Top row: name + status badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${espInfo.color}`}>
            {espInfo.label}
          </span>
          <p className="text-sm font-medium text-foreground">
            {connection.name}
          </p>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            connection.status === "connected"
              ? "bg-status-success/10 text-status-success"
              : "bg-status-danger/10 text-status-danger"
          }`}
        >
          {connection.status === "connected"
            ? "Connected"
            : "Error"}
        </span>
      </div>

      {/* Meta row */}
      <div className="mt-3 flex items-center gap-4 text-xs text-foreground-muted">
        <span>{`Credentials: ****\${connection.credentials_hint}`}</span>
        <span>
          {lastSynced
            ? `Last synced \${lastSynced}`
            : "Never synced"}
        </span>
      </div>

      {/* Actions */}
      <div className="mt-3 flex items-center gap-2 border-t border-card-border pt-3">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-status-danger transition-colors hover:bg-surface-hover"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {"Delete"}
        </button>
      </div>
    </div>
  );
}
