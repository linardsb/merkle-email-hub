"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  Bug,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import {
  useFailurePatterns,
  useFailurePatternStats,
} from "@/hooks/use-failure-patterns";
import { FailurePatternStatsCards } from "@/components/failure-patterns/stats-cards";
import { FailurePatternFilters } from "@/components/failure-patterns/filters";
import { FailurePatternTable } from "@/components/failure-patterns/pattern-table";
import { FailurePatternDetailDialog } from "@/components/failure-patterns/detail-dialog";
import type { FailurePatternResponse } from "@/types/failure-patterns";

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

export default function FailurePatternsPage() {
  const t = useTranslations("failurePatterns");
  const [page, setPage] = useState(1);
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [checkFilter, setCheckFilter] = useState<string>("");
  const [selectedPattern, setSelectedPattern] =
    useState<FailurePatternResponse | null>(null);

  const { data, isLoading, error, mutate } = useFailurePatterns({
    page,
    pageSize: 20,
    agentName: agentFilter || undefined,
    qaCheck: checkFilter || undefined,
  });
  const { data: stats, isLoading: statsLoading } = useFailurePatternStats();

  // Loading state
  if (isLoading || statsLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-foreground-accent" />
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
        <Skeleton className="h-12 rounded-lg border border-card-border" />
        <Skeleton className="h-64 rounded-lg border border-card-border" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-foreground-accent" />
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

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  // Empty state
  if (total === 0 && !agentFilter && !checkFilter) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              {t("title")}
            </h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <EmptyState
          icon={Bug}
          title={t("noPatterns")}
          description={t("noPatternsDescription")}
        />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-8 w-8 text-foreground-accent" />
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            {t("title")}
          </h1>
          <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && <FailurePatternStatsCards stats={stats} />}

      {/* Filters */}
      <FailurePatternFilters
        agents={AGENTS}
        checks={QA_CHECKS}
        agentFilter={agentFilter}
        checkFilter={checkFilter}
        onAgentChange={(v) => {
          setAgentFilter(v);
          setPage(1);
        }}
        onCheckChange={(v) => {
          setCheckFilter(v);
          setPage(1);
        }}
      />

      {/* Pattern Table */}
      <FailurePatternTable patterns={items} onSelect={setSelectedPattern} />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-foreground-muted">
            {t("page", { current: page, total: totalPages })}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex items-center gap-1 rounded border border-card-border px-3 py-1.5 text-sm text-foreground disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" /> {t("previous")}
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="flex items-center gap-1 rounded border border-card-border px-3 py-1.5 text-sm text-foreground disabled:opacity-50"
            >
              {t("next")} <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Detail Dialog */}
      {selectedPattern && (
        <FailurePatternDetailDialog
          pattern={selectedPattern}
          onClose={() => setSelectedPattern(null)}
        />
      )}
    </div>
  );
}
