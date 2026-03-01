"use client";

import { useTranslations } from "next-intl";
import { Download, Plug, Cloud, Palette, Mail } from "lucide-react";
import { ExportStatusBadge } from "./export-status-badge";
import type { ExportHistoryRecord, ConnectorPlatform } from "@/types/connectors";

const PLATFORM_CONFIG: Record<ConnectorPlatform, { labelKey: string; icon: typeof Plug }> = {
  braze: { labelKey: "platformBraze", icon: Plug },
  sfmc: { labelKey: "platformSfmc", icon: Cloud },
  adobe_campaign: { labelKey: "platformAdobeCampaign", icon: Palette },
  taxi: { labelKey: "platformTaxi", icon: Mail },
  raw_html: { labelKey: "platformRawHtml", icon: Download },
};

interface ExportCardProps {
  record: ExportHistoryRecord;
}

export function ExportCard({ record }: ExportCardProps) {
  const t = useTranslations("connectors");

  const config = PLATFORM_CONFIG[record.platform];
  const platformLabel = t(config.labelKey);
  const PlatformIcon = config.icon;

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-surface-muted">
            <PlatformIcon className="h-5 w-5 text-foreground-muted" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              {record.name}
            </p>
            <p className="text-xs text-foreground-muted">{platformLabel}</p>
          </div>
        </div>
        <ExportStatusBadge status={record.status} />
      </div>
      {record.error_message && (
        <p className="mt-2 text-xs text-status-danger">
          {record.error_message}
        </p>
      )}
      <p className="mt-3 text-xs text-foreground-muted">
        {new Date(record.created_at).toLocaleString()}
      </p>
    </div>
  );
}
