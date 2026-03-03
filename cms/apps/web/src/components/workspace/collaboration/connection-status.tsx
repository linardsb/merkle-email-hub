"use client";

import { useTranslations } from "next-intl";
import type { CollaborationStatus } from "@/types/collaboration";

interface ConnectionStatusProps {
  status: CollaborationStatus;
}

const STATUS_CONFIG: Record<CollaborationStatus, { dotClass: string; labelKey: string }> = {
  connected: { dotClass: "bg-success", labelKey: "connected" },
  connecting: { dotClass: "bg-warning animate-pulse", labelKey: "reconnecting" },
  disconnected: { dotClass: "bg-destructive", labelKey: "disconnected" },
};

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const t = useTranslations("collaboration");
  const config = STATUS_CONFIG[status];

  return (
    <div className="flex items-center gap-1.5" title={t(config.labelKey)}>
      <span className={`inline-block h-2 w-2 rounded-full ${config.dotClass}`} />
      <span className="text-[10px] text-muted">{t(config.labelKey)}</span>
    </div>
  );
}
