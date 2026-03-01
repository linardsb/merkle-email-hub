"use client";

import { FileText } from "lucide-react";
import { useTranslations } from "next-intl";
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
  const t = useTranslations("knowledge");

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-lg border border-card-border bg-card-bg p-5 text-left transition-colors hover:bg-surface-hover"
    >
      <div className="flex items-start gap-3">
        <FileText className="mt-0.5 h-5 w-5 shrink-0 text-foreground-accent" />
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-medium text-foreground">
            {document.title ?? document.filename}
          </h3>
          {document.description && (
            <p className="mt-1 line-clamp-2 text-sm text-foreground-muted">
              {document.description}
            </p>
          )}
        </div>
      </div>

      {/* Tags */}
      {document.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {document.tags.map((tag) => (
            <span
              key={tag.id}
              className="rounded-full bg-surface-muted px-2 py-0.5 text-xs text-foreground-muted"
            >
              {tag.name}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between text-xs text-foreground-muted">
        <span>{DOMAIN_LABELS[document.domain] ?? document.domain}</span>
        <span>{t("chunks", { count: document.chunk_count })}</span>
      </div>
    </button>
  );
}
