"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { BookOpen, Search } from "lucide-react";
import {
  useKnowledgeDocuments,
  useKnowledgeDomains,
  useKnowledgeTags,
  useKnowledgeSearch,
} from "@/hooks/use-knowledge";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import {
  SkeletonSearchResult,
  SkeletonKnowledgeCard,
} from "@/components/ui/skeletons";
import { KnowledgeSearchResultCard } from "@/components/knowledge/knowledge-search-result";
import { KnowledgeDocumentCard } from "@/components/knowledge/knowledge-document-card";
import { KnowledgeDocumentDialog } from "@/components/knowledge/knowledge-document-dialog";

const PAGE_SIZE = 12;

const DOMAIN_LABELS: Record<string, string> = {
  css_support: "CSS Support",
  best_practices: "Best Practices",
  client_quirks: "Client Quirks",
};

export default function KnowledgePage() {
  const t = useTranslations("knowledge");

  // ── State ──
  const [searchInput, setSearchInput] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [activeDomain, setActiveDomain] = useState<string | undefined>(
    undefined,
  );
  const [activeTag, setActiveTag] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // ── Debounce search ──
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // ── Data fetching ──
  const isSearchMode = debouncedQuery.length > 0;

  // Browse mode: paginated documents
  const {
    data: documentsData,
    isLoading: docsLoading,
    error: docsError,
    mutate: docsMutate,
  } = useKnowledgeDocuments({
    page,
    pageSize: PAGE_SIZE,
    domain: activeDomain,
    tag: activeTag,
  });

  // Search mode: POST search
  const {
    trigger: triggerSearch,
    data: searchData,
    isMutating: searchLoading,
    error: searchError,
  } = useKnowledgeSearch();

  // Domains & tags for filters
  const { data: domainsData } = useKnowledgeDomains();
  const { data: tagsData } = useKnowledgeTags();

  // ── Trigger search when query changes ──
  useEffect(() => {
    if (debouncedQuery) {
      triggerSearch({
        query: debouncedQuery,
        domain: activeDomain,
        limit: 20,
      });
    }
  }, [debouncedQuery, activeDomain, triggerSearch]);

  // ── Handlers ──
  const handleDomainChange = useCallback(
    (domain: string | undefined) => {
      setActiveDomain(domain);
      setPage(1);
    },
    [],
  );

  const handleTagChange = useCallback((tag: string | undefined) => {
    setActiveTag((prev) => (prev === tag ? undefined : tag));
    setPage(1);
  }, []);

  const handleViewDocument = useCallback((docId: number) => {
    setSelectedDocId(docId);
    setDialogOpen(true);
  }, []);

  // ── Pagination ──
  const totalPages = documentsData
    ? Math.ceil(documentsData.total / PAGE_SIZE)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <BookOpen className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">
            {t("title")}
          </h1>
        </div>
        <p className="mt-1 text-sm text-foreground-muted">{t("subtitle")}</p>
      </div>

      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={t("searchPlaceholder")}
          className="w-full rounded-lg border border-input-border bg-input-bg py-3 pl-10 pr-4 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
          aria-label={t("searchPlaceholder")}
        />
      </div>

      {/* Domain filter pills */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => handleDomainChange(undefined)}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            !activeDomain
              ? "bg-interactive text-foreground-inverse"
              : "bg-surface-muted text-foreground-muted hover:bg-surface-hover hover:text-foreground"
          }`}
        >
          {t("allDomains")}
        </button>
        {(domainsData?.domains ?? []).map((domain) => (
          <button
            key={domain}
            type="button"
            onClick={() => handleDomainChange(domain)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeDomain === domain
                ? "bg-interactive text-foreground-inverse"
                : "bg-surface-muted text-foreground-muted hover:bg-surface-hover hover:text-foreground"
            }`}
          >
            {DOMAIN_LABELS[domain] ?? domain}
          </button>
        ))}
      </div>

      {/* Tag filter pills */}
      {tagsData?.tags && tagsData.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tagsData.tags.map((tag) => (
            <button
              key={tag.id}
              type="button"
              onClick={() => handleTagChange(tag.name)}
              className={`rounded-full px-2.5 py-0.5 text-xs transition-colors ${
                activeTag === tag.name
                  ? "bg-interactive/15 font-medium text-interactive"
                  : "bg-surface-muted text-foreground-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              {tag.name}
            </button>
          ))}
        </div>
      )}

      {/* ── Search Results Mode ── */}
      {isSearchMode && (
        <>
          {searchData && !searchLoading && (
            <p className="text-sm text-foreground-muted">
              {t("searchResultsCount", {
                count: searchData.results.length,
                total: searchData.total_candidates,
              })}
            </p>
          )}

          {searchLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonSearchResult key={i} />
              ))}
            </div>
          ) : searchError ? (
            <ErrorState
              message={t("searchError")}
              onRetry={() =>
                triggerSearch({
                  query: debouncedQuery,
                  domain: activeDomain,
                  limit: 20,
                })
              }
              retryLabel={t("retry")}
            />
          ) : searchData?.results.length === 0 ? (
            <EmptyState
              icon={Search}
              title={t("noSearchResults")}
              description={t("noSearchResultsDescription")}
            />
          ) : (
            <div className="animate-fade-in space-y-3">
              {searchData?.results.map((result, i) => (
                <KnowledgeSearchResultCard
                  key={`${result.document_id}-${result.chunk_index}-${i}`}
                  result={result}
                  onViewDocument={handleViewDocument}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Browse Mode ── */}
      {!isSearchMode && (
        <>
          {documentsData && !docsLoading && (
            <p className="text-sm text-foreground-muted">
              {t("documentCount", { count: documentsData.total })}
            </p>
          )}

          {docsLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonKnowledgeCard key={i} />
              ))}
            </div>
          ) : docsError ? (
            <ErrorState
              message={t("browseError")}
              onRetry={() => docsMutate()}
              retryLabel={t("retry")}
            />
          ) : documentsData?.items.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title={t("noDocuments")}
              description={t("noDocumentsDescription")}
            />
          ) : (
            <div className="animate-fade-in grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {documentsData?.items.map((doc) => (
                <KnowledgeDocumentCard
                  key={doc.id}
                  document={doc}
                  onClick={() => handleViewDocument(doc.id)}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {documentsData && totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-foreground-muted">
                {t("showing", {
                  from: (page - 1) * PAGE_SIZE + 1,
                  to: Math.min(page * PAGE_SIZE, documentsData.total),
                  total: documentsData.total,
                })}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-md border border-border px-3 py-1 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
                >
                  {t("previous")}
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="rounded-md border border-border px-3 py-1 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
                >
                  {t("next")}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Document detail dialog */}
      <KnowledgeDocumentDialog
        documentId={selectedDocId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  );
}
