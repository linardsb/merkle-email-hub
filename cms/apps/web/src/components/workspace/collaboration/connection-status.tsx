"use client";

import type { CollaborationStatus } from "@/types/collaboration";

interface ConnectionStatusProps {
  status: CollaborationStatus;
}

const STATUS_CONFIG: Record<CollaborationStatus, { dotClass: string; label: string }> = {
  connected: { dotClass: "bg-success", label: "Connected" },
  connecting: { dotClass: "bg-warning animate-pulse", label: "Reconnecting" },
  disconnected: { dotClass: "bg-destructive", label: "Disconnected" },
};

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const config = STATUS_CONFIG[status];

  return (
    <div className="flex items-center gap-1.5" title={config.label}>
      <span className={`inline-block h-2 w-2 rounded-full ${config.dotClass}`} />
      <span className="text-muted-foreground text-[10px]">{config.label}</span>
    </div>
  );
}
