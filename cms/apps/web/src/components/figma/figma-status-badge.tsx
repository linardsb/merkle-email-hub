import type { FigmaConnectionStatus } from "@/types/figma";

const STATUS_STYLES: Record<FigmaConnectionStatus, string> = {
  connected: "bg-badge-success-bg text-badge-success-text",
  syncing: "bg-badge-warning-bg text-badge-warning-text",
  error: "bg-badge-danger-bg text-badge-danger-text",
  disconnected: "bg-surface-muted text-foreground-muted",
};

const STATUS_LABELS: Record<FigmaConnectionStatus, string> = {
  connected: "Connected",
  syncing: "Syncing",
  error: "Error",
  disconnected: "Disconnected",
};

interface FigmaStatusBadgeProps {
  status: FigmaConnectionStatus;
}

export function FigmaStatusBadge({ status }: FigmaStatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
