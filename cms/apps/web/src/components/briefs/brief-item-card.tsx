"use client";

import { Calendar, Users } from "lucide-react";
import type { BriefItem } from "@/types/briefs";

const STATUS_STYLES: Record<string, string> = {
  open: "bg-badge-info-bg text-badge-info-text",
  in_progress: "bg-badge-warning-bg text-badge-warning-text",
  done: "bg-badge-success-bg text-badge-success-text",
  cancelled: "bg-surface-muted text-foreground-muted",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  in_progress: "In Progress",
  done: "Done",
  cancelled: "Cancelled",
};

interface BriefItemCardProps {
  item: BriefItem;
  onSelect: () => void;
}

export function BriefItemCard({ item, onSelect }: BriefItemCardProps) {
  const dueDate = item.due_date
    ? new Date(item.due_date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full rounded-lg border border-card-border bg-card-bg p-3 text-left transition-colors hover:bg-surface-hover"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-mono text-foreground-muted">{item.external_id}</p>
          <p className="mt-0.5 text-sm font-medium text-foreground line-clamp-2">
            {item.title}
          </p>
        </div>
        <span
          className={`shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[item.status] ?? ""}`}
        >
          {STATUS_LABELS[item.status] ?? "Open"}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-3 text-xs text-foreground-muted">
        {item.assignees.length > 0 && (
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            {item.assignees.slice(0, 2).join(", ")}
            {item.assignees.length > 2 && ` +${item.assignees.length - 2}`}
          </span>
        )}
        {dueDate && (
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {dueDate}
          </span>
        )}
      </div>

      {item.labels.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {item.labels.slice(0, 3).map((label) => (
            <span
              key={label}
              className="rounded bg-surface-muted px-1.5 py-0.5 text-xs text-foreground-muted"
            >
              {label}
            </span>
          ))}
          {item.labels.length > 3 && (
            <span className="text-xs text-foreground-muted">+{item.labels.length - 3}</span>
          )}
        </div>
      )}
    </button>
  );
}
