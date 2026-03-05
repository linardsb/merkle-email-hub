"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { MonitorSmartphone, ChevronLeft, ChevronRight, GitCompareArrows } from "lucide-react";
import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useRenderingTests } from "@/hooks/use-renderings";
import { RenderingStatsCards } from "@/components/renderings/rendering-stats-cards";
import { ClientCompatibilityMatrix } from "@/components/renderings/client-compatibility-matrix";
import { RenderingTestList } from "@/components/renderings/rendering-test-list";
import { RenderingTestDialog } from "@/components/renderings/rendering-test-dialog";
import { RenderingScreenshotDialog } from "@/components/renderings/rendering-screenshot-dialog";
import { VisualRegressionDialog } from "@/components/renderings/visual-regression-dialog";
import type { ScreenshotResult } from "@/types/rendering";

export default function RenderingsPage() {
  const t = useTranslations("renderings");

  const [page, setPage] = useState(1);
  const { data: testsData, isLoading, error, mutate } = useRenderingTests({ page, pageSize: 10 });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [screenshotResult, setScreenshotResult] = useState<ScreenshotResult | null>(null);
  const [screenshotOpen, setScreenshotOpen] = useState(false);

  // Compare state: select two test IDs
  const [compareIds, setCompareIds] = useState<[number | null, number | null]>([null, null]);
  const [compareOpen, setCompareOpen] = useState(false);

  const handleScreenshotClick = useCallback((result: ScreenshotResult) => {
    setScreenshotResult(result);
    setScreenshotOpen(true);
  }, []);

  const handleCompareToggle = useCallback((testId: number) => {
    setCompareIds((prev) => {
      if (prev[0] === testId) return [prev[1], null];
      if (prev[1] === testId) return [prev[0], null];
      if (prev[0] === null) return [testId, prev[1]];
      return [prev[0], testId];
    });
  }, []);

  const tests = testsData?.items ?? [];
  const totalPages = testsData ? Math.ceil(testsData.total / testsData.page_size) : 1;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <MonitorSmartphone className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg border border-card-border" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-lg border border-card-border" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <MonitorSmartphone className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
        </div>
        <ErrorState message={t("error")} onRetry={() => mutate()} retryLabel={t("retry")} />
      </div>
    );
  }

  if (tests.length === 0 && page === 1) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MonitorSmartphone className="h-8 w-8 text-foreground-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
              <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
            </div>
          </div>
          <button
            onClick={() => setDialogOpen(true)}
            className="rounded bg-foreground-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            {t("requestTest")}
          </button>
        </div>
        <EmptyState
          icon={MonitorSmartphone}
          title={t("noTests")}
          description={t("noTestsDescription")}
        />
        <RenderingTestDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          onTestSubmitted={() => mutate()}
        />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MonitorSmartphone className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {compareIds[0] !== null && compareIds[1] !== null && (
            <button
              onClick={() => setCompareOpen(true)}
              className="flex items-center gap-1.5 rounded border border-card-border bg-card-bg px-3 py-2 text-sm font-medium text-foreground hover:bg-surface-muted"
            >
              <GitCompareArrows className="h-4 w-4" />
              {t("compareTests")}
            </button>
          )}
          <button
            onClick={() => setDialogOpen(true)}
            className="rounded bg-foreground-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            {t("requestTest")}
          </button>
        </div>
      </div>

      {/* Stats */}
      <RenderingStatsCards tests={tests} />

      {/* Compatibility Matrix */}
      <ClientCompatibilityMatrix tests={tests} />

      {/* Test List */}
      <RenderingTestList
        tests={tests}
        onScreenshotClick={handleScreenshotClick}
        compareIds={compareIds}
        onCompareToggle={handleCompareToggle}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="flex items-center gap-1 rounded border border-card-border px-3 py-1.5 text-sm text-foreground-muted hover:text-foreground disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" />
            {t("prevPage")}
          </button>
          <span className="text-sm text-foreground-muted">
            {t("pageOf", { page, total: totalPages })}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="flex items-center gap-1 rounded border border-card-border px-3 py-1.5 text-sm text-foreground-muted hover:text-foreground disabled:opacity-40"
          >
            {t("nextPage")}
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Dialogs */}
      <RenderingTestDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onTestSubmitted={() => mutate()}
      />
      <RenderingScreenshotDialog
        open={screenshotOpen}
        onOpenChange={setScreenshotOpen}
        result={screenshotResult}
      />
      <VisualRegressionDialog
        open={compareOpen}
        onOpenChange={setCompareOpen}
        baselineTestId={compareIds[0]}
        currentTestId={compareIds[1]}
      />
    </div>
  );
}
