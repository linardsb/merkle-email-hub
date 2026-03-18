"use client";

import type { ExportHistoryRecord } from "@/types/connectors";

const STATUS_STYLES: Record<ExportHistoryRecord["status"], string> = {
  success: "bg-badge-success-bg text-badge-success-text",
  failed: "bg-badge-danger-bg text-badge-danger-text",
  exporting: "bg-badge-warning-bg text-badge-warning-text",
};

const STATUS_LABELS: Record<ExportHistoryRecord["status"], string> = {
  success: "Success",
  failed: "Failed",
  exporting: "Exporting",
};

interface ExportStatusBadgeProps {
  status: ExportHistoryRecord["status"];
}

export function ExportStatusBadge({ status }: ExportStatusBadgeProps) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
