"use client";

import { useTranslations } from "next-intl";
import type { ExportHistoryRecord } from "@/types/connectors";

const STATUS_STYLES: Record<ExportHistoryRecord["status"], string> = {
  success: "bg-badge-success-bg text-badge-success-text",
  failed: "bg-badge-danger-bg text-badge-danger-text",
  exporting: "bg-badge-warning-bg text-badge-warning-text",
};

const STATUS_KEYS: Record<ExportHistoryRecord["status"], string> = {
  success: "statusSuccess",
  failed: "statusFailed",
  exporting: "statusExporting",
};

interface ExportStatusBadgeProps {
  status: ExportHistoryRecord["status"];
}

export function ExportStatusBadge({ status }: ExportStatusBadgeProps) {
  const t = useTranslations("connectors");

  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {t(STATUS_KEYS[status])}
    </span>
  );
}
