import { useTranslations } from "next-intl";
import type { BriefConnectionStatus } from "@/types/briefs";

const STATUS_STYLES: Record<BriefConnectionStatus, string> = {
  connected: "bg-badge-success-bg text-badge-success-text",
  syncing: "bg-badge-warning-bg text-badge-warning-text",
  error: "bg-badge-danger-bg text-badge-danger-text",
  disconnected: "bg-surface-muted text-foreground-muted",
};

const STATUS_LABEL_KEYS: Record<BriefConnectionStatus, string> = {
  connected: "statusConnected",
  syncing: "statusSyncing",
  error: "statusError",
  disconnected: "statusDisconnected",
};

interface BriefStatusBadgeProps {
  status: BriefConnectionStatus;
}

export function BriefStatusBadge({ status }: BriefStatusBadgeProps) {
  const t = useTranslations("briefs");

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {t(STATUS_LABEL_KEYS[status])}
    </span>
  );
}
