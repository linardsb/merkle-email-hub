"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { ClipboardCheck } from "lucide-react";
import { useProjects } from "@/hooks/use-projects";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonListItem } from "@/components/ui/skeletons";
import { useApprovals } from "@/hooks/use-approvals";
import { ApprovalCard } from "@/components/approvals/approval-card";
import type { ApprovalResponse } from "@merkle-email-hub/sdk";

const STATUS_FILTERS = [
  "all",
  "pending",
  "approved",
  "rejected",
  "revision_requested",
] as const;

const FILTER_LABEL_KEYS: Record<string, string> = {
  all: "filterAll",
  pending: "filterPending",
  approved: "filterApproved",
  rejected: "filterRejected",
  revision_requested: "filterRevision",
};

export default function ApprovalsPage() {
  const t = useTranslations("approvals");
  const router = useRouter();

  const [activeFilter, setActiveFilter] = useState<string>("all");

  // Load user's projects to get approvals across all of them
  const { data: projects, isLoading: loadingProjects } = useProjects();

  // For MVP, load approvals for first project
  const firstProjectId = projects?.items?.[0]?.id ?? null;
  const {
    data: approvals,
    isLoading: loadingApprovals,
    error,
    mutate,
  } = useApprovals(firstProjectId);

  const filtered = useMemo(() => {
    if (!approvals) return [];
    if (activeFilter === "all") return approvals;
    return approvals.filter((a) => a.status === activeFilter);
  }, [approvals, activeFilter]);

  const isLoading = loadingProjects || loadingApprovals;

  const handleApprovalClick = (approval: ApprovalResponse) => {
    router.push(`/approvals/${approval.id}`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ClipboardCheck className="h-6 w-6 text-foreground" />
        <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-2">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter}
            type="button"
            onClick={() => setActiveFilter(filter)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeFilter === filter
                ? "bg-interactive text-foreground-inverse"
                : "bg-surface-muted text-foreground-muted hover:text-foreground"
            }`}
          >
            {t(FILTER_LABEL_KEYS[filter] ?? "filterAll")}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonListItem key={i} />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={t("error")} onRetry={() => mutate()} retryLabel={t("retry")} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={ClipboardCheck}
          title={t("empty")}
          description={t("emptyDescription")}
        />
      ) : (
        <div className="animate-fade-in grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onClick={handleApprovalClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}
