"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { MonitorSmartphone } from "lucide-react";
import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";
import { useRenderingSummary } from "@/hooks/use-renderings";

export function RenderingSummaryCard() {
  const t = useTranslations("renderings");
  const { data, isLoading } = useRenderingSummary();

  if (isLoading) {
    return <Skeleton className="h-40 rounded-lg border border-card-border" />;
  }

  if (!data || data.total_tests === 0) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MonitorSmartphone className="h-5 w-5 text-foreground-muted" />
            <h2 className="text-lg font-semibold text-foreground">{t("clientRendering")}</h2>
          </div>
          <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs font-medium text-foreground-muted">
            {t("noData")}
          </span>
        </div>
        <p className="mt-2 text-sm text-foreground-muted">{t("noTestsDescription")}</p>
      </div>
    );
  }

  const scoreColor =
    data.latest_score >= 80
      ? "text-status-success"
      : data.latest_score >= 60
        ? "text-status-warning"
        : "text-status-danger";

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MonitorSmartphone className="h-5 w-5 text-foreground-muted" />
          <h2 className="text-lg font-semibold text-foreground">{t("clientRendering")}</h2>
        </div>
        <Link
          href="/renderings"
          className="text-sm text-foreground-accent hover:underline"
        >
          {t("viewAllRenderings")}
        </Link>
      </div>

      <div className="mt-4 flex items-start gap-6">
        <div>
          <p className="text-sm text-foreground-muted">{t("clientRenderingScore")}</p>
          <p className={`text-3xl font-bold ${scoreColor}`}>{data.latest_score}%</p>
        </div>

        <div className="flex-1">
          <p className="mb-2 text-sm text-foreground-muted">{t("clientRenderingProblematic")}</p>
          <div className="space-y-1.5">
            {data.problematic_clients.slice(0, 3).map((client) => (
              <div key={client.client_id} className="flex items-center gap-2">
                <span className="w-24 truncate text-sm capitalize text-foreground">
                  {client.client_name.replace(/_/g, " ")}
                </span>
                <div className="flex-1">
                  <div className="h-1.5 overflow-hidden rounded-full bg-surface-muted">
                    <div
                      className="h-full rounded-full bg-status-danger"
                      style={{ width: `${Math.min(client.fail_rate, 100)}%` }}
                    />
                  </div>
                </div>
                <span className="w-10 text-right text-xs text-foreground-muted">
                  {Math.round(client.fail_rate)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
