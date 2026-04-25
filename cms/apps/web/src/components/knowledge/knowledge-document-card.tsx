"use client";

import { FileText } from "../icons";
import type { KnowledgeDocument } from "@/types/knowledge";

const DOMAIN_LABELS: Record<string, string> = {
  css_support: "CSS Support",
  best_practices: "Best Practices",
  client_quirks: "Client Quirks",
};

interface Props {
  document: KnowledgeDocument;
  onClick: () => void;
}

export function KnowledgeDocumentCard({ document, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="border-card-border bg-card-bg hover:bg-surface-hover w-full rounded-lg border p-5 text-left transition-colors"
    >
      <div className="flex items-start gap-3">
        <FileText className="text-foreground-accent mt-0.5 h-5 w-5 shrink-0" />
        <div className="min-w-0 flex-1">
          <h3 className="text-foreground truncate font-medium">
            {document.title ?? document.filename}
          </h3>
          {document.description && (
            <p className="text-foreground-muted mt-1 line-clamp-2 text-sm">
              {document.description}
            </p>
          )}
        </div>
      </div>

      {/* Tags */}
      {(document.tags ?? []).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {(document.tags ?? []).map((tag) => (
            <span
              key={tag.id}
              className="bg-surface-muted text-foreground-muted rounded-full px-2 py-0.5 text-xs"
            >
              {tag.name}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="text-foreground-muted mt-3 flex items-center justify-between text-xs">
        <span>{DOMAIN_LABELS[document.domain] ?? document.domain}</span>
        <span>{`${document.chunk_count} chunks`}</span>
      </div>
    </button>
  );
}
