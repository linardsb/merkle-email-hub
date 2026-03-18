"use client";

import { useState, useEffect, useMemo } from "react";
import { Search, Building2 } from "lucide-react";
import { SkeletonCard } from "@/components/ui/skeletons";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { BriefCampaignCard } from "./brief-campaign-card";
import { BriefDetailDialog } from "./brief-detail-dialog";
import { useAllBriefItems, useBriefConnections } from "@/hooks/use-briefs";
import type { BriefPlatform, BriefItemStatus } from "@/types/briefs";
import { ClipboardList } from "lucide-react";

const PLATFORM_LABELS: Record<string, string> = {
  jira: "Jira",
  asana: "Asana",
  monday: "Monday.com",
  clickup: "ClickUp",
  trello: "Trello",
  notion: "Notion",
  wrike: "Wrike",
  basecamp: "Basecamp",
};

const STATUS_FILTERS: BriefItemStatus[] = ["open", "in_progress", "done", "cancelled"];

const STATUS_LABELS: Record<BriefItemStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  done: "Done",
  cancelled: "Cancelled",
};

export function BriefsOverview() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [platformFilter, setPlatformFilter] = useState<BriefPlatform | undefined>();
  const [statusFilter, setStatusFilter] = useState<BriefItemStatus | undefined>();
  const [clientFilter, setClientFilter] = useState<string | undefined>();
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

  // Gather unique platforms from all connections for filter pills
  const connectedPlatforms = connections
    ? [...new Set(connections.map((c) => c.platform))]
    : [];

  // Gather unique client names from loaded items
  const clientNames = useMemo(() => {
    if (!items) return [];
    const names = new Set<string>();
    for (const item of items) {
      if (item.client_name) names.add(item.client_name);
    }
    return [...names].sort();
  }, [items]);

  // Apply client filter locally (on top of server-side platform/status/search)
  const filteredItems = useMemo(() => {
    if (!items) return [];
    if (!clientFilter) return items;
    return items.filter((item) => item.client_name === clientFilter);
  }, [items, clientFilter]);

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
          placeholder={"Search briefs..."}
          className="w-full rounded-md border border-input-border bg-input-bg py-2 pl-10 pr-4 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
          aria-label={"Search briefs..."}
        />
      </div>

      {/* Client filter pills */}
      {clientNames.length > 1 && (
        <div className="flex flex-wrap items-center gap-2">
          <Building2 className="h-3.5 w-3.5 text-foreground-muted" />
          <button
            type="button"
            onClick={() => setClientFilter(undefined)}
            className={`${pillBase} ${!clientFilter ? pillActive : pillInactive}`}
          >
            {"All"}
          </button>
          {clientNames.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => setClientFilter(clientFilter === name ? undefined : name)}
              className={`${pillBase} ${clientFilter === name ? pillActive : pillInactive}`}
            >
              {name}
            </button>
          ))}
        </div>
      )}

      {/* Platform + status filter pills */}
      <div className="flex flex-wrap gap-2">
        {/* Platform filters */}
        <button
          type="button"
          onClick={() => setPlatformFilter(undefined)}
          className={`${pillBase} ${!platformFilter ? pillActive : pillInactive}`}
        >
          {"All"}
        </button>
        {connectedPlatforms.map((platform) => (
          <button
            key={platform}
            type="button"
            onClick={() => setPlatformFilter(platformFilter === platform ? undefined : platform)}
            className={`${pillBase} ${platformFilter === platform ? pillActive : pillInactive}`}
          >
            {PLATFORM_LABELS[platform] ?? platform}
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
            {STATUS_LABELS[status]}
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
          message={"Failed to load briefs"}
          onRetry={() => mutate()}
          retryLabel={"Try again"}
        />
      ) : filteredItems.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title={"No briefs yet"}
          description={"Connect a platform to start syncing campaign briefs"}
        />
      ) : (
        <>
          <p className="text-sm text-foreground-muted">
            {`\${filteredItems.length} briefs`}
          </p>
          <div className="animate-fade-in grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredItems.map((item) => (
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
