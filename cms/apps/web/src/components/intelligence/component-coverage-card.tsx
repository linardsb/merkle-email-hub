"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Puzzle } from "lucide-react";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useComponentCoverage } from "@/hooks/use-intelligence-stats";

const BADGE_COLORS: Record<string, string> = {
  full: "bg-status-success",
  partial: "bg-status-warning",
  issues: "bg-status-danger",
  untested: "bg-surface-muted",
};

export function ComponentCoverageCard() {
  const t = useTranslations("intelligence");
  const { coverage, isLoading } = useComponentCoverage();

  if (isLoading) {
    return <Skeleton className="h-40 rounded-lg border border-card-border" />;
  }

  if (coverage.total === 0) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg p-6">
        <div className="flex items-center gap-2">
          <Puzzle className="h-5 w-5 text-foreground-muted" />
          <h2 className="text-lg font-semibold text-foreground">
            {t("componentCoverage")}
          </h2>
        </div>
        <p className="mt-2 text-sm text-foreground-muted">
          {t("noComponents")}
        </p>
      </div>
    );
  }

  const segments = [
    { key: "full", count: coverage.full, label: t("coverageFull") },
    { key: "partial", count: coverage.partial, label: t("coveragePartial") },
    { key: "issues", count: coverage.issues, label: t("coverageIssues") },
    { key: "untested", count: coverage.untested, label: t("coverageUntested") },
  ];

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Puzzle className="h-5 w-5 text-foreground-muted" />
          <h2 className="text-lg font-semibold text-foreground">
            {t("componentCoverage")}
          </h2>
        </div>
        <Link
          href="/components"
          className="text-sm text-foreground-accent hover:underline"
        >
          {t("viewComponents")}
        </Link>
      </div>
      <p className="mt-1 text-sm text-foreground-muted">
        {t("componentCoverageDescription", { total: coverage.total })}
      </p>

      {/* Stacked bar */}
      <div className="mt-4 flex h-4 overflow-hidden rounded-full">
        {segments.map((seg) =>
          seg.count > 0 ? (
            <div
              key={seg.key}
              className={`${BADGE_COLORS[seg.key]} transition-all`}
              style={{ width: `${(seg.count / coverage.total) * 100}%` }}
              title={`${seg.label}: ${seg.count}`}
            />
          ) : null
        )}
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-4">
        {segments.map((seg) => (
          <div key={seg.key} className="flex items-center gap-1.5">
            <div
              className={`h-2.5 w-2.5 rounded-full ${BADGE_COLORS[seg.key]}`}
            />
            <span className="text-xs text-foreground-muted">
              {seg.label} ({seg.count})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
