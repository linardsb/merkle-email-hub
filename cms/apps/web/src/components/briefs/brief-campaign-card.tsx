"use client";

import { useTranslations } from "next-intl";
import { Calendar, Users, ImageOff } from "lucide-react";
import { BriefPlatformBadge } from "./brief-platform-badge";
import { BriefResourceLinks } from "./brief-resource-links";
import type { BriefItem } from "@/types/briefs";

const STATUS_STYLES: Record<string, string> = {
  open: "bg-badge-info-bg text-badge-info-text",
  in_progress: "bg-badge-warning-bg text-badge-warning-text",
  done: "bg-badge-success-bg text-badge-success-text",
  cancelled: "bg-surface-muted text-foreground-muted",
};

const STATUS_KEYS: Record<string, string> = {
  open: "itemStatusOpen",
  in_progress: "itemStatusInProgress",
  done: "itemStatusDone",
  cancelled: "itemStatusCancelled",
};

interface BriefCampaignCardProps {
  item: BriefItem;
  onClick: () => void;
}

export function BriefCampaignCard({ item, onClick }: BriefCampaignCardProps) {
  const t = useTranslations("briefs");

  const dueDate = item.due_date
    ? new Date(item.due_date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full overflow-hidden rounded-lg border border-card-border bg-card-bg text-left transition-colors hover:bg-surface-hover"
    >
      {/* Thumbnail */}
      <div className="relative aspect-[16/9] w-full overflow-hidden bg-surface-muted">
        {item.thumbnail_url ? (
          <img
            src={item.thumbnail_url}
            alt={item.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <ImageOff className="h-8 w-8 text-foreground-muted opacity-40" />
          </div>
        )}
        {item.platform && (
          <div className="absolute right-2 top-2">
            <BriefPlatformBadge platform={item.platform} />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="space-y-2 p-3">
        {/* ID + Status */}
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-xs text-foreground-muted">{item.external_id}</span>
          <span
            className={`shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[item.status] ?? ""}`}
          >
            {t(STATUS_KEYS[item.status] ?? "itemStatusOpen")}
          </span>
        </div>

        {/* Title */}
        <p className="text-sm font-medium text-foreground line-clamp-2">{item.title}</p>

        {/* Connection name */}
        {item.connection_name && (
          <p className="text-xs text-foreground-muted">{item.connection_name}</p>
        )}

        {/* Meta row */}
        <div className="flex items-center gap-3 text-xs text-foreground-muted">
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

        {/* Resources */}
        {item.resources.length > 0 && <BriefResourceLinks resources={item.resources} />}
      </div>
    </button>
  );
}
