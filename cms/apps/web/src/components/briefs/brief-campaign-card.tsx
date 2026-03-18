"use client";

import { Calendar, Users, ImageOff, Building2 } from "lucide-react";
import { BriefPlatformBadge } from "./brief-platform-badge";
import { BriefResourceLinks } from "./brief-resource-links";
import type { BriefItem, BriefPlatform } from "@/types/briefs";

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

// Deterministic color assignment for client names
const CLIENT_COLORS = [
  "#2563EB", // blue
  "#DC2626", // red
  "#059669", // emerald
  "#D97706", // amber
  "#7C3AED", // violet
  "#DB2777", // pink
  "#0891B2", // cyan
  "#4F46E5", // indigo
  "#CA8A04", // yellow
  "#0D9488", // teal
];

function getClientColor(clientName: string): string {
  let hash = 0;
  for (let i = 0; i < clientName.length; i++) {
    hash = clientName.charCodeAt(i) + ((hash << 5) - hash);
  }
  const idx = Math.abs(hash) % CLIENT_COLORS.length;
  return CLIENT_COLORS[idx] as string;
}

interface BriefCampaignCardProps {
  item: BriefItem;
  onClick: () => void;
}

export function BriefCampaignCard({ item, onClick }: BriefCampaignCardProps) {
  const dueDate = item.due_date
    ? new Date(item.due_date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : null;

  const clientColor = item.client_name ? getClientColor(item.client_name) : undefined;

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
        {/* Client tag — solid color, bottom-left overlay on thumbnail */}
        {item.client_name && clientColor && (
          <div
            className="absolute bottom-2 left-2 rounded px-2.5 py-1 text-xs font-bold text-white shadow-sm"
            style={{ backgroundColor: clientColor }}
          >
            {item.client_name}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="space-y-2 p-3">
        {/* Client pill + Status row */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {item.client_name && clientColor ? (
              <span
                className="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold text-white"
                style={{ backgroundColor: clientColor }}
              >
                <Building2 className="h-3 w-3" />
                {item.client_name}
              </span>
            ) : null}
            <span className="font-mono text-xs text-foreground-muted truncate">{item.external_id}</span>
          </div>
          <span
            className={`shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[item.status] ?? ""}`}
          >
            {STATUS_LABELS[item.status] ?? "Open"}
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
