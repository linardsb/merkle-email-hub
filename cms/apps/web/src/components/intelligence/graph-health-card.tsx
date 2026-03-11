"use client";

import { useTranslations } from "next-intl";
import { Network } from "lucide-react";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useGraphHealth } from "@/hooks/use-intelligence-stats";

export function GraphHealthCard() {
  const t = useTranslations("intelligence");
  const { data, isLoading } = useGraphHealth();

  if (isLoading) {
    return <Skeleton className="h-24 rounded-lg border border-card-border" />;
  }

  const healthy = data?.healthy ?? false;

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <div className="flex items-center gap-2">
        <Network className="h-4 w-4 text-foreground-muted" />
        <p className="text-sm font-medium text-foreground-muted">
          {t("graphHealth")}
        </p>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <div
          className={`h-3 w-3 rounded-full ${
            healthy ? "bg-status-success" : "bg-status-danger"
          }`}
        />
        <p
          className={`text-lg font-semibold ${
            healthy ? "text-status-success" : "text-status-danger"
          }`}
        >
          {healthy ? t("graphOnline") : t("graphOffline")}
        </p>
      </div>
      <p className="mt-1 text-xs text-foreground-muted">
        {t("graphHealthDescription")}
      </p>
    </div>
  );
}
