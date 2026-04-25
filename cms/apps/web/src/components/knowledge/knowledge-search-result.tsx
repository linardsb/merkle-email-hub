"use client";

import { FileText } from "../icons";
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

export function KnowledgeSearchResultCard({ result, onViewDocument }: Props) {
  const scorePercent = Math.round(result.score * 100);

  return (
    <div className="border-card-border bg-card-bg hover:bg-surface-hover rounded-lg border p-4 transition-colors">
      {/* Header: filename + domain badge */}
      <div className="flex items-center gap-2">
        <FileText className="text-foreground-muted h-4 w-4 shrink-0" />
        <span className="text-foreground truncate text-sm font-medium">
          {result.document_filename}
        </span>
        <span className="bg-surface-muted text-foreground-muted shrink-0 rounded-full px-2 py-0.5 text-xs">
          {DOMAIN_LABELS[result.domain] ?? result.domain}
        </span>
      </div>

      {/* Chunk content preview */}
      <p className="text-foreground-muted mt-2 line-clamp-3 text-sm leading-relaxed">
        {result.chunk_content}
      </p>

      {/* Footer: relevance score + view button */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="bg-surface-muted h-1.5 w-20 rounded-full">
            <div
              className="bg-interactive h-full rounded-full"
              style={{ width: `${scorePercent}%` }}
            />
          </div>
          <span className="text-foreground-muted text-xs">{`${scorePercent}% match`}</span>
        </div>
        <button
          type="button"
          onClick={() => onViewDocument(result.document_id)}
          className="text-interactive text-xs font-medium hover:underline"
        >
          {"View Document"}
        </button>
      </div>
    </div>
  );
}
