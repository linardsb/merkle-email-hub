"use client";

import { useState, useMemo, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Blocks, Search } from "lucide-react";
import { useComponents } from "@/hooks/use-components";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonComponentCard } from "@/components/ui/skeletons";
import { ComponentCard } from "@/components/components/component-card";
import { ComponentDetailDialog } from "@/components/components/component-detail-dialog";

const PAGE_SIZE = 12;

export default function ComponentsPage() {
  const t = useTranslations("components");

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [selectedComponentId, setSelectedComponentId] = useState<number | null>(
    null
  );
  const [dialogOpen, setDialogOpen] = useState(false);

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

  // Extract unique categories from loaded data
  const categories = useMemo(() => {
    if (!data?.items) return [];
    const cats = new Set<string>();
    for (const item of data.items) {
      if (item.category) cats.add(item.category);
    }
    return Array.from(cats).sort();
  }, [data?.items]);

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
      <div className="flex items-center gap-3">
        <Blocks className="h-8 w-8 text-foreground-accent" />
        <h1 className="text-2xl font-semibold text-foreground">
          {t("title")}
        </h1>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("searchPlaceholder")}
          className="w-full rounded-md border border-input-border bg-input-bg py-2 pl-10 pr-4 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
          aria-label={t("searchPlaceholder")}
        />
      </div>

      {/* Category filter */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleCategoryChange(undefined)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              !category
                ? "bg-interactive text-foreground-inverse"
                : "bg-surface-muted text-foreground-muted hover:bg-surface-hover hover:text-foreground"
            }`}
          >
            {t("allCategories")}
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => handleCategoryChange(cat)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                category === cat
                  ? "bg-interactive text-foreground-inverse"
                  : "bg-surface-muted text-foreground-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonComponentCard key={i} />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={t("error")} onRetry={() => mutate()} retryLabel={t("retry")} />
      ) : data?.items.length === 0 ? (
        <div className="rounded-lg border border-card-border bg-card-bg px-4 py-12 text-center">
          <Blocks className="mx-auto h-10 w-10 text-foreground-muted" />
          <p className="mt-3 text-sm font-medium text-foreground">
            {t("noComponents")}
          </p>
          <p className="mt-1 text-xs text-foreground-muted">
            {t("noComponentsDescription")}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
            {t("showing", {
              from: (page - 1) * PAGE_SIZE + 1,
              to: Math.min(page * PAGE_SIZE, data.total),
              total: data.total,
            })}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t("previous")}
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t("next")}
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
    </div>
  );
}
