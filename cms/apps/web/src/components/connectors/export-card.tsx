"use client";

import { Download, Plug, Cloud, Palette, Mail } from "../icons";
import { ExportStatusBadge } from "./export-status-badge";
import type { ExportHistoryRecord, ConnectorPlatform } from "@/types/connectors";

const PLATFORM_CONFIG: Record<ConnectorPlatform, { label: string; icon: typeof Plug }> = {
  braze: { label: "Braze Content Block", icon: Plug },
  sfmc: { label: "Salesforce Marketing Cloud", icon: Cloud },
  adobe_campaign: { label: "Adobe Campaign", icon: Palette },
  taxi: { label: "Taxi for Email", icon: Mail },
  raw_html: { label: "Raw HTML Download", icon: Download },
};

interface ExportCardProps {
  record: ExportHistoryRecord;
}

export function ExportCard({ record }: ExportCardProps) {
  const config = PLATFORM_CONFIG[record.platform];
  const platformLabel = config.label;
  const PlatformIcon = config.icon;

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-surface-muted flex h-10 w-10 items-center justify-center rounded-md">
            <PlatformIcon className="text-foreground-muted h-5 w-5" />
          </div>
          <div>
            <p className="text-foreground text-sm font-medium">{record.name}</p>
            <p className="text-foreground-muted text-xs">{platformLabel}</p>
          </div>
        </div>
        <ExportStatusBadge status={record.status} />
      </div>
      {record.error_message && (
        <p className="text-status-danger mt-2 text-xs">{record.error_message}</p>
      )}
      <p className="text-foreground-muted mt-3 text-xs">
        {new Date(record.created_at).toLocaleString()}
      </p>
    </div>
  );
}
