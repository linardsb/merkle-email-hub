"use client";

import { useTranslations } from "next-intl";
import {
  BarChart3,
  ListChecks,
  TrendingUp,
  Clock,
} from "lucide-react";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useQADashboard } from "@/hooks/use-qa-dashboard";
import { ScoreOverviewCards } from "@/components/intelligence/score-overview-cards";
import { CheckPerformanceChart } from "@/components/intelligence/check-performance-chart";
import { ScoreTrendBars } from "@/components/intelligence/score-trend-bars";
import { RecentResultsTable } from "@/components/intelligence/recent-results-table";
import { ExportReportMenu } from "@/components/intelligence/export-report-menu";
import { RenderingSummaryCard } from "@/components/intelligence/rendering-summary-card";
import { GraphHealthCard } from "@/components/intelligence/graph-health-card";
import { BlueprintSuccessCard } from "@/components/intelligence/blueprint-success-card";
import { AgentPerformanceChart } from "@/components/intelligence/agent-performance-chart";
import { TopFailurePatternsCard } from "@/components/intelligence/top-failure-patterns-card";
import { ComponentCoverageCard } from "@/components/intelligence/component-coverage-card";

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
        <ErrorState
          message={t("error")}
          onRetry={() => mutate()}
          retryLabel={t("retry")}
        />
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
        <EmptyState
          icon={BarChart3}
          title={t("noResults")}
          description={t("noResultsDescription")}
        />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              {t("title")}
            </h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <ExportReportMenu metrics={metrics} />
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

      {/* Email Client Rendering */}
      <RenderingSummaryCard />

      {/* Graph & Blueprint Overview */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <GraphHealthCard />
        <BlueprintSuccessCard />
        <ComponentCoverageCard />
      </div>

      {/* Agent Performance & Failure Patterns */}
      <div className="grid gap-4 lg:grid-cols-2">
        <AgentPerformanceChart />
        <TopFailurePatternsCard />
      </div>
    </div>
  );
}
