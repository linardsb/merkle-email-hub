"use client";

import { useTranslations } from "next-intl";
import { Workflow, AlertTriangle, Users, ListChecks } from "lucide-react";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useFailurePatternStats } from "@/hooks/use-failure-patterns";

export function BlueprintSuccessCard() {
  const t = useTranslations("intelligence");
  const { data: stats, isLoading } = useFailurePatternStats();

  if (isLoading) {
    return <Skeleton className="h-40 rounded-lg border border-card-border" />;
  }

  const totalPatterns = stats?.total_patterns ?? 0;
  const uniqueAgents = stats?.unique_agents ?? 0;
  const uniqueChecks = stats?.unique_checks ?? 0;
  const topCheck = stats?.top_check?.replace(/_/g, " ") ?? "—";

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <div className="flex items-center gap-2">
        <Workflow className="h-5 w-5 text-foreground-muted" />
        <h2 className="text-lg font-semibold text-foreground">
          {t("blueprintHealth")}
        </h2>
      </div>
      <p className="mt-1 text-sm text-foreground-muted">
        {t("blueprintHealthDescription")}
      </p>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-status-warning" />
          <div>
            <p className="text-xs text-foreground-muted">
              {t("totalPatterns")}
            </p>
            <p className="text-lg font-semibold text-foreground">
              {totalPatterns}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-foreground-muted" />
          <div>
            <p className="text-xs text-foreground-muted">
              {t("uniqueAgents")}
            </p>
            <p className="text-lg font-semibold text-foreground">
              {uniqueAgents}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ListChecks className="h-4 w-4 text-foreground-muted" />
          <div>
            <p className="text-xs text-foreground-muted">
              {t("uniqueChecks")}
            </p>
            <p className="text-lg font-semibold text-foreground">
              {uniqueChecks}
            </p>
          </div>
        </div>
        <div>
          <p className="text-xs text-foreground-muted">{t("topCheck")}</p>
          <p className="text-sm font-medium text-foreground capitalize">
            {topCheck}
          </p>
        </div>
      </div>
    </div>
  );
}
