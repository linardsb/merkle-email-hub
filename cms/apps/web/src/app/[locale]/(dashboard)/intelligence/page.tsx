"use client";

import { useTranslations } from "next-intl";
import {
  BarChart3,
  ListChecks,
  TrendingUp,
  Clock,
  MonitorSmartphone,
} from "lucide-react";
import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";
import { useQADashboard } from "@/hooks/use-qa-dashboard";
import { ScoreOverviewCards } from "@/components/intelligence/score-overview-cards";
import { CheckPerformanceChart } from "@/components/intelligence/check-performance-chart";
import { ScoreTrendBars } from "@/components/intelligence/score-trend-bars";
import { RecentResultsTable } from "@/components/intelligence/recent-results-table";

export default function IntelligencePage() {
  const t = useTranslations("intelligence");
  const { metrics, isLoading, error, mutate } = useQADashboard();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              {t("title")}
            </h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton
              key={i}
              className="h-24 rounded-lg border border-card-border"
            />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton
              key={i}
              className="h-64 rounded-lg border border-card-border"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">
            {t("title")}
          </h1>
        </div>
        <div className="rounded-lg border border-card-border bg-card-bg px-4 py-12 text-center">
          <p className="text-sm text-status-danger">{t("error")}</p>
          <button
            type="button"
            onClick={() => mutate()}
            className="mt-3 text-sm text-interactive hover:underline"
          >
            {t("retry")}
          </button>
        </div>
      </div>
    );
  }

  if (metrics.totalRuns === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              {t("title")}
            </h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <div className="rounded-lg border border-card-border bg-card-bg p-8 text-center">
          <BarChart3 className="mx-auto h-12 w-12 text-foreground-muted" />
          <h3 className="mt-4 text-lg font-semibold text-foreground">
            {t("noResults")}
          </h3>
          <p className="mt-2 text-sm text-foreground-muted">
            {t("noResultsDescription")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart3 className="h-8 w-8 text-foreground-accent" />
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            {t("title")}
          </h1>
          <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
        </div>
      </div>

      {/* Overview cards */}
      <ScoreOverviewCards metrics={metrics} />

      {/* Charts row */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Check Performance */}
        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-foreground-muted" />
            <h2 className="text-lg font-semibold text-foreground">
              {t("checkPerformance")}
            </h2>
          </div>
          <p className="mt-1 text-sm text-foreground-muted">
            {t("checkPerformanceDescription")}
          </p>
          <div className="mt-4">
            <CheckPerformanceChart checkAverages={metrics.checkAverages} />
          </div>
        </div>

        {/* Score Trend */}
        <div className="rounded-lg border border-card-border bg-card-bg p-6">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-foreground-muted" />
            <h2 className="text-lg font-semibold text-foreground">
              {t("scoreTrend")}
            </h2>
          </div>
          <p className="mt-1 text-sm text-foreground-muted">
            {t("scoreTrendDescription")}
          </p>
          <div className="mt-4">
            <ScoreTrendBars scoreTrend={metrics.scoreTrend} />
          </div>
        </div>
      </div>

      {/* Recent Results */}
      <div className="rounded-lg border border-card-border bg-card-bg p-6">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-foreground-muted" />
          <h2 className="text-lg font-semibold text-foreground">
            {t("recentResults")}
          </h2>
        </div>
        <p className="mt-1 text-sm text-foreground-muted">
          {t("recentResultsDescription")}
        </p>
        <div className="mt-4">
          <RecentResultsTable />
        </div>
      </div>

      {/* Email Client Rendering — Coming Soon */}
      <div className="rounded-lg border border-card-border bg-card-bg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MonitorSmartphone className="h-5 w-5 text-foreground-muted" />
            <h2 className="text-lg font-semibold text-foreground">
              {t("clientRendering")}
            </h2>
          </div>
          <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs font-medium text-foreground-muted">
            {t("comingSoon")}
          </span>
        </div>
        <p className="mt-2 text-sm text-foreground-muted">
          {t("clientRenderingDescription")}
        </p>
      </div>
    </div>
  );
}
