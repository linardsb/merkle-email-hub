"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Search } from "lucide-react";
import { SkeletonCard } from "@/components/ui/skeletons";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { BriefCampaignCard } from "./brief-campaign-card";
import { BriefDetailDialog } from "./brief-detail-dialog";
import { useAllBriefItems, useBriefConnections } from "@/hooks/use-briefs";
import type { BriefPlatform, BriefItemStatus } from "@/types/briefs";
import { ClipboardList } from "lucide-react";

const STATUS_FILTERS: BriefItemStatus[] = ["open", "in_progress", "done", "cancelled"];

const STATUS_LABEL_KEYS: Record<BriefItemStatus, string> = {
  open: "itemStatusOpen",
  in_progress: "itemStatusInProgress",
  done: "itemStatusDone",
  cancelled: "itemStatusCancelled",
};

export function BriefsOverview() {
  const t = useTranslations("briefs");

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [platformFilter, setPlatformFilter] = useState<BriefPlatform | undefined>();
  const [statusFilter, setStatusFilter] = useState<BriefItemStatus | undefined>();
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data: connections } = useBriefConnections();
  const { data: items, isLoading, error, mutate } = useAllBriefItems({
    platform: platformFilter,
    status: statusFilter,
    search: debouncedSearch || undefined,
  });

  // Gather unique connected platforms for filter pills
  const connectedPlatforms = connections
    ? [...new Set(connections.filter((c) => c.status === "connected").map((c) => c.platform))]
    : [];

  const pillBase = "rounded-full px-3 py-1 text-xs font-medium transition-colors";
  const pillActive = "bg-interactive text-foreground-inverse";
  const pillInactive = "bg-surface-muted text-foreground-muted hover:bg-surface-hover hover:text-foreground";

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("searchBriefs")}
          className="w-full rounded-md border border-input-border bg-input-bg py-2 pl-10 pr-4 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
          aria-label={t("searchBriefs")}
        />
      </div>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2">
        {/* Platform filters */}
        <button
          type="button"
          onClick={() => setPlatformFilter(undefined)}
          className={`${pillBase} ${!platformFilter ? pillActive : pillInactive}`}
        >
          {t("filterAll")}
        </button>
        {connectedPlatforms.map((platform) => (
          <button
            key={platform}
            type="button"
            onClick={() => setPlatformFilter(platformFilter === platform ? undefined : platform)}
            className={`${pillBase} ${platformFilter === platform ? pillActive : pillInactive}`}
          >
            {t(`platform${platform.charAt(0).toUpperCase()}${platform.slice(1)}` as Parameters<typeof t>[0])}
          </button>
        ))}

        {/* Separator */}
        {connectedPlatforms.length > 0 && (
          <span className="mx-1 self-center text-foreground-muted">|</span>
        )}

        {/* Status filters */}
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setStatusFilter(statusFilter === status ? undefined : status)}
            className={`${pillBase} ${statusFilter === status ? pillActive : pillInactive}`}
          >
            {t(STATUS_LABEL_KEYS[status])}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : error ? (
        <ErrorState
          message={t("allBriefsError")}
          onRetry={() => mutate()}
          retryLabel={t("retry")}
        />
      ) : !items || items.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title={t("allBriefsEmpty")}
          description={t("allBriefsEmptyDescription")}
        />
      ) : (
        <>
          <p className="text-sm text-foreground-muted">
            {t("briefCount", { count: items.length })}
          </p>
          <div className="animate-fade-in grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <BriefCampaignCard
                key={item.id}
                item={item}
                onClick={() => setSelectedItemId(item.id)}
              />
            ))}
          </div>
        </>
      )}

      <BriefDetailDialog
        itemId={selectedItemId}
        open={selectedItemId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedItemId(null);
        }}
      />
    </div>
  );
}
