"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";
import {
  useKnowledgeDocument,
  useKnowledgeDocumentContent,
} from "@/hooks/use-knowledge";

type Tab = "content" | "metadata";

interface Props {
  documentId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function KnowledgeDocumentDialog({
  documentId,
  open,
  onOpenChange,
}: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("content");

  const { data: doc } = useKnowledgeDocument(documentId);
  const { data: content } = useKnowledgeDocumentContent(documentId);

  const tabs: { key: Tab; label: string }[] = [
    { key: "content", label: "Content" },
    { key: "metadata", label: "Metadata" },
  ];

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            {doc?.title ?? doc?.filename ?? "Document Details"}
          </DialogTitle>
          {doc?.description && (
            <p className="text-sm text-foreground-muted">{doc.description}</p>
          )}
        </DialogHeader>

        {/* Document meta summary */}
        {doc && (
          <div className="flex flex-wrap items-center gap-3 text-xs text-foreground-muted">
            <span className="rounded-full bg-surface-muted px-2 py-0.5">
              {doc.domain.replace(/_/g, " ")}
            </span>
            <span>{`${doc.chunk_count} chunks`}</span>
            <span>{formatDate(doc.created_at)}</span>
          </div>
        )}

        {/* Tags */}
        {doc?.tags && doc.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {doc.tags.map((tag) => (
              <span
                key={tag.id}
                className="rounded-full bg-surface-muted px-2 py-0.5 text-xs font-medium text-interactive"
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}

        {/* Tab bar */}
        <div className="flex gap-1 border-b border-border" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-b-2 border-interactive text-foreground"
                  : "text-foreground-muted hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="mt-2">
          {activeTab === "content" && (
            <ScrollArea className="max-h-96">
              {content?.chunks && content.chunks.length > 0 ? (
                <div className="space-y-3 pr-4">
                  {content.chunks.map((chunk) => (
                    <div
                      key={chunk.chunk_index}
                      className="rounded-md bg-surface-muted p-3"
                    >
                      <p className="mb-1 text-xs font-medium text-foreground-muted">
                        {`Chunk ${chunk.chunk_index + 1}`}
                      </p>
                      <p className="whitespace-pre-wrap text-sm text-foreground">
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-foreground-muted">
                  {"No content available"}
                </p>
              )}
            </ScrollArea>
          )}

          {activeTab === "metadata" && doc && (
            <div className="space-y-2 text-sm">
              {(
                [
                  ["Filename", doc.filename],
                  ["Source Type", doc.source_type],
                  ["Language", doc.language],
                  ["Status", doc.status],
                  ["Total Chunks", String(doc.chunk_count)],
                  ["Created", formatDate(doc.created_at)],
                  ["Last Updated", formatDate(doc.updated_at)],
                ] as const
              ).map(([label, value]) => (
                <div
                  key={label}
                  className="flex justify-between border-b border-border py-2"
                >
                  <span className="text-foreground-muted">{label}</span>
                  <span className="font-medium text-foreground">{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
