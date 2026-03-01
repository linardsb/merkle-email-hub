"use client";

import { FileText } from "lucide-react";
import { useTranslations } from "next-intl";
import type { KnowledgeSearchResult } from "@/types/knowledge";

const DOMAIN_LABELS: Record<string, string> = {
  css_support: "CSS Support",
  best_practices: "Best Practices",
  client_quirks: "Client Quirks",
};

interface Props {
  result: KnowledgeSearchResult;
  onViewDocument: (documentId: number) => void;
}

export function KnowledgeSearchResultCard({
  result,
  onViewDocument,
}: Props) {
  const t = useTranslations("knowledge");
  const scorePercent = Math.round(result.score * 100);

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-4 transition-colors hover:bg-surface-hover">
      {/* Header: filename + domain badge */}
      <div className="flex items-center gap-2">
        <FileText className="h-4 w-4 shrink-0 text-foreground-muted" />
        <span className="truncate text-sm font-medium text-foreground">
          {result.document_filename}
        </span>
        <span className="shrink-0 rounded-full bg-surface-muted px-2 py-0.5 text-xs text-foreground-muted">
          {DOMAIN_LABELS[result.domain] ?? result.domain}
        </span>
      </div>

      {/* Chunk content preview */}
      <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-foreground-muted">
        {result.chunk_content}
      </p>

      {/* Footer: relevance score + view button */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-20 rounded-full bg-surface-muted">
            <div
              className="h-full rounded-full bg-interactive"
              style={{ width: `${scorePercent}%` }}
            />
          </div>
          <span className="text-xs text-foreground-muted">
            {t("relevance", { score: scorePercent })}
          </span>
        </div>
        <button
          type="button"
          onClick={() => onViewDocument(result.document_id)}
          className="text-xs font-medium text-interactive hover:underline"
        >
          {t("viewDocument")}
        </button>
      </div>
    </div>
  );
}
