"use client";

import { useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  MonitorSmartphone,
  ChevronLeft,
  ChevronRight,
  GitCompareArrows,
  Bug,
} from "../../../components/icons";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useRenderingTests } from "@/hooks/use-renderings";
import { RenderingStatsCards } from "@/components/renderings/rendering-stats-cards";
import { ClientCompatibilityMatrix } from "@/components/renderings/client-compatibility-matrix";
import { RenderingTestList } from "@/components/renderings/rendering-test-list";
import { RenderingTestDialog } from "@/components/renderings/rendering-test-dialog";
import { RenderingScreenshotDialog } from "@/components/renderings/rendering-screenshot-dialog";
import { VisualRegressionDialog } from "@/components/renderings/visual-regression-dialog";
import { useFailurePatterns, useFailurePatternStats } from "@/hooks/use-failure-patterns";
import { FailurePatternStatsCards } from "@/components/failure-patterns/stats-cards";
import { FailurePatternFilters } from "@/components/failure-patterns/filters";
import { FailurePatternTable } from "@/components/failure-patterns/pattern-table";
import { FailurePatternDetailDialog } from "@/components/failure-patterns/detail-dialog";
import type { ScreenshotResult } from "@/types/rendering";
import { RenderingDashboard } from "@/components/rendering/rendering-dashboard";
import type { FailurePatternResponse } from "@/types/failure-patterns";

type Tab = "tests" | "patterns" | "dashboard";

const AGENTS: string[] = [
  "scaffolder",
  "dark_mode",
  "content",
  "outlook_fixer",
  "accessibility",
  "personalisation",
  "code_reviewer",
  "knowledge",
  "innovation",
];

const QA_CHECKS: string[] = [
  "html_validation",
  "css_support",
  "file_size",
  "link_validation",
  "spam_score",
  "dark_mode",
  "accessibility",
  "fallback",
  "image_optimization",
  "brand_compliance",
];

export default function RenderingsPage() {
  const searchParams = useSearchParams();

  const initialTab = searchParams.get("tab");
  const [tab, setTab] = useState<Tab>(
    initialTab === "patterns" ? "patterns" : initialTab === "dashboard" ? "dashboard" : "tests",
  );

  // --- Rendering Tests state ---
  const [page, setPage] = useState(1);
  const { data: testsData, isLoading, error, mutate } = useRenderingTests({ page, pageSize: 10 });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [screenshotResult, setScreenshotResult] = useState<ScreenshotResult | null>(null);
  const [screenshotOpen, setScreenshotOpen] = useState(false);
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

  // --- Failure Patterns state ---
  const [fpPage, setFpPage] = useState(1);
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [checkFilter, setCheckFilter] = useState<string>("");
  const [selectedPattern, setSelectedPattern] = useState<FailurePatternResponse | null>(null);

  const {
    data: fpData,
    isLoading: fpLoading,
    error: fpError,
    mutate: fpMutate,
  } = useFailurePatterns({
    page: fpPage,
    pageSize: 20,
    agentName: agentFilter || undefined,
    qaCheck: checkFilter || undefined,
  });
  const { data: fpStats, isLoading: fpStatsLoading } = useFailurePatternStats();

  const fpItems = fpData?.items ?? [];
  const fpTotal = fpData?.total ?? 0;
  const fpTotalPages = Math.ceil(fpTotal / 20);

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MonitorSmartphone className="text-foreground-accent h-8 w-8" />
          <div>
            <h1 className="text-foreground text-2xl font-semibold">{"Rendering Preview"}</h1>
            <p className="text-foreground-muted text-sm">
              {"Cross-client email rendering tests powered by Litmus and Email on Acid"}
            </p>
          </div>
        </div>
        {tab === "tests" && (
          <div className="flex items-center gap-2">
            {compareIds[0] !== null && compareIds[1] !== null && (
              <button
                onClick={() => setCompareOpen(true)}
                className="border-card-border bg-card-bg text-foreground hover:bg-surface-muted flex items-center gap-1.5 rounded border px-3 py-2 text-sm font-medium"
              >
                <GitCompareArrows className="h-4 w-4" />
                {"Compare"}
              </button>
            )}
            <button
              onClick={() => setDialogOpen(true)}
              className="bg-foreground-accent rounded px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              {"Request Rendering Test"}
            </button>
          </div>
        )}
      </div>

      {/* Tab bar */}
      <div className="border-card-border bg-card-bg flex gap-1 rounded-lg border p-1">
        <button
          onClick={() => setTab("tests")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "tests"
              ? "bg-interactive text-foreground-inverse"
              : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
          }`}
        >
          {"Rendering Tests"}
        </button>
        <button
          onClick={() => setTab("patterns")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "patterns"
              ? "bg-interactive text-foreground-inverse"
              : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
          }`}
        >
          {"Failure Patterns"}
        </button>
        <button
          onClick={() => setTab("dashboard")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "dashboard"
              ? "bg-interactive text-foreground-inverse"
              : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
          }`}
        >
          {"Dashboard"}
        </button>
      </div>

      {/* Tab content */}
      {tab === "dashboard" && <RenderingDashboard html={null} projectId={null} />}

      {tab === "tests" && (
        <>
          {isLoading ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="border-card-border h-24 rounded-lg border" />
                ))}
              </div>
              <Skeleton className="border-card-border h-64 rounded-lg border" />
            </>
          ) : error ? (
            <ErrorState
              message={"Failed to load rendering data"}
              onRetry={() => mutate()}
              retryLabel={"Try again"}
            />
          ) : tests.length === 0 && page === 1 ? (
            <>
              <EmptyState
                icon={MonitorSmartphone}
                title={"No rendering tests yet"}
                description={
                  "Run your first cross-client rendering test to see how your emails look everywhere."
                }
              />
            </>
          ) : (
            <>
              <RenderingStatsCards tests={tests} />
              <ClientCompatibilityMatrix tests={tests} />
              <RenderingTestList
                tests={tests}
                onScreenshotClick={handleScreenshotClick}
                compareIds={compareIds}
                onCompareToggle={handleCompareToggle}
              />
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-4">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="border-card-border text-foreground-muted hover:text-foreground flex items-center gap-1 rounded border px-3 py-1.5 text-sm disabled:opacity-40"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    {"Previous"}
                  </button>
                  <span className="text-foreground-muted text-sm">
                    {`Page ${page} of ${totalPages}`}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="border-card-border text-foreground-muted hover:text-foreground flex items-center gap-1 rounded border px-3 py-1.5 text-sm disabled:opacity-40"
                  >
                    {"Next"}
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}

      {tab === "patterns" && (
        <>
          {fpLoading || fpStatsLoading ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="border-card-border h-24 rounded-lg border" />
                ))}
              </div>
              <Skeleton className="border-card-border h-12 rounded-lg border" />
              <Skeleton className="border-card-border h-64 rounded-lg border" />
            </>
          ) : fpError ? (
            <ErrorState
              message={"Failed to load failure patterns"}
              onRetry={() => fpMutate()}
              retryLabel={"Try again"}
            />
          ) : fpTotal === 0 && !agentFilter && !checkFilter ? (
            <EmptyState
              icon={Bug}
              title={"No Failure Patterns"}
              description={
                "Run blueprint pipelines with QA checks to discover failure patterns across agents."
              }
            />
          ) : (
            <>
              {fpStats && <FailurePatternStatsCards stats={fpStats} />}
              <FailurePatternFilters
                agents={AGENTS}
                checks={QA_CHECKS}
                agentFilter={agentFilter}
                checkFilter={checkFilter}
                onAgentChange={(v) => {
                  setAgentFilter(v);
                  setFpPage(1);
                }}
                onCheckChange={(v) => {
                  setCheckFilter(v);
                  setFpPage(1);
                }}
              />
              <FailurePatternTable patterns={fpItems} onSelect={setSelectedPattern} />
              {fpTotalPages > 1 && (
                <div className="flex items-center justify-between">
                  <span className="text-foreground-muted text-sm">
                    {`Page ${fpPage} of ${fpTotalPages}`}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setFpPage((p) => Math.max(1, p - 1))}
                      disabled={fpPage <= 1}
                      className="border-card-border text-foreground flex items-center gap-1 rounded border px-3 py-1.5 text-sm disabled:opacity-50"
                    >
                      <ChevronLeft className="h-4 w-4" /> {"Previous"}
                    </button>
                    <button
                      onClick={() => setFpPage((p) => Math.min(fpTotalPages, p + 1))}
                      disabled={fpPage >= fpTotalPages}
                      className="border-card-border text-foreground flex items-center gap-1 rounded border px-3 py-1.5 text-sm disabled:opacity-50"
                    >
                      {"Next"} <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
              {selectedPattern && (
                <FailurePatternDetailDialog
                  pattern={selectedPattern}
                  onClose={() => setSelectedPattern(null)}
                />
              )}
            </>
          )}
        </>
      )}

      {/* Rendering dialogs (always mounted for test tab) */}
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
