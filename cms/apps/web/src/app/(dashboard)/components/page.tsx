"use client";

import { useState, useEffect } from "react";
import { FileCode, Search, Plus } from "../../../components/icons";
import { useSession } from "next-auth/react";
import { useComponents } from "@/hooks/use-components";
import { SECTION_CATEGORIES } from "@/types/visual-builder";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonComponentCard } from "@/components/ui/skeletons";
import { ComponentCard } from "@/components/components/component-card";
import { ComponentDetailDialog } from "@/components/components/component-detail-dialog";
import { CreateComponentDialog } from "@/components/components/create-component-dialog";

const PAGE_SIZE = 12;

export default function ComponentsPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [selectedComponentId, setSelectedComponentId] = useState<number | null>(
    null
  );
  const [dialogOpen, setDialogOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const session = useSession();
  const userRole = session.data?.user?.role;
  const canCreate = userRole === "admin" || userRole === "developer";

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isLoading, error, mutate } = useComponents({
    page,
    pageSize: PAGE_SIZE,
    category,
    search: debouncedSearch || undefined,
  });

  const categories = SECTION_CATEGORIES;

  const totalPages = data
    ? Math.ceil(data.total / PAGE_SIZE)
    : 0;

  const handleCardClick = (id: number) => {
    setSelectedComponentId(id);
    setDialogOpen(true);
  };

  const handleCategoryChange = (cat: string | undefined) => {
    setCategory(cat);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileCode className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">
            {"Component Library"}
          </h1>
        </div>
        {canCreate && (
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-2 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
          >
            <Plus className="h-4 w-4" />
            {"Create Component"}
          </button>
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={"Search components..."}
          className="w-full rounded-md border border-input-border bg-input-bg py-2 pl-10 pr-4 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
          aria-label={"Search components..."}
        />
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => handleCategoryChange(undefined)}
          className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
            !category
              ? "bg-interactive text-foreground-inverse"
              : "bg-surface-muted text-foreground-muted hover:bg-surface-hover hover:text-foreground"
          }`}
        >
          {"All Categories"}
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => handleCategoryChange(cat)}
            className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
              category === cat
                ? "bg-interactive text-foreground-inverse"
                : "bg-surface-muted text-foreground-muted hover:bg-surface-hover hover:text-foreground"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonComponentCard key={i} />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={"Failed to load components"} onRetry={() => mutate()} retryLabel={"Try again"} />
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon={FileCode}
          title={"No components found"}
          description={"Email components will appear here once they are created."}
        />
      ) : (
        <div className="animate-fade-in grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data?.items.map((component) => (
            <ComponentCard
              key={component.id}
              component={component}
              onClick={() => handleCardClick(component.id)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-foreground-muted">
            {`Showing ${(page - 1) * PAGE_SIZE + 1}-${Math.min(page * PAGE_SIZE, data.total)} of ${data.total}`}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {"Previous"}
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {"Next"}
            </button>
          </div>
        </div>
      )}

      {/* Detail dialog */}
      <ComponentDetailDialog
        componentId={selectedComponentId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />

      {/* Create dialog */}
      <CreateComponentDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
