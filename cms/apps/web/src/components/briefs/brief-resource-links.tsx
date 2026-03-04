"use client";

import { FileSpreadsheet, FileText, Image, Languages, Paperclip } from "lucide-react";
import type { BriefResource, BriefResourceType } from "@/types/briefs";

const RESOURCE_ICONS: Record<BriefResourceType, typeof FileText> = {
  excel: FileSpreadsheet,
  translation: Languages,
  design: Image,
  document: FileText,
  image: Image,
  other: Paperclip,
};

interface BriefResourceLinksProps {
  resources: BriefResource[];
  maxVisible?: number;
}

export function BriefResourceLinks({ resources, maxVisible = 3 }: BriefResourceLinksProps) {
  if (resources.length === 0) return null;

  const visible = resources.slice(0, maxVisible);
  const remaining = resources.length - maxVisible;

  return (
    <div className="flex flex-wrap gap-1.5">
      {visible.map((resource) => {
        const Icon = RESOURCE_ICONS[resource.type] ?? Paperclip;
        return (
          <a
            key={resource.id}
            href={resource.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 rounded border border-card-border bg-surface-muted px-2 py-1 text-xs text-foreground-muted transition-colors hover:bg-surface-hover hover:text-foreground"
            title={resource.filename}
          >
            <Icon className="h-3 w-3 shrink-0" />
            <span className="max-w-[6rem] truncate">{resource.filename}</span>
          </a>
        );
      })}
      {remaining > 0 && (
        <span className="inline-flex items-center rounded bg-surface-muted px-2 py-1 text-xs text-foreground-muted">
          +{remaining}
        </span>
      )}
    </div>
  );
}
