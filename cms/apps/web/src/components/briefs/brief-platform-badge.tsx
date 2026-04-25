"use client";

import type { BriefPlatform } from "@/types/briefs";

const PLATFORM_COLORS: Record<BriefPlatform, string> = {
  jira: "#2684FF",
  asana: "#F06A6A",
  monday: "#6C3CE1",
  clickup: "#7B68EE",
  trello: "#0079BF",
  notion: "#787774",
  wrike: "#08CF65",
  basecamp: "#F5A623",
};

const PLATFORM_LABELS: Record<BriefPlatform, string> = {
  jira: "Jira",
  asana: "Asana",
  monday: "Monday.com",
  clickup: "ClickUp",
  trello: "Trello",
  notion: "Notion",
  wrike: "Wrike",
  basecamp: "Basecamp",
};

interface BriefPlatformBadgeProps {
  platform: BriefPlatform;
  size?: "sm" | "md";
}

export function BriefPlatformBadge({ platform, size = "sm" }: BriefPlatformBadgeProps) {
  return (
    <span
      className={`bg-surface-muted inline-flex items-center gap-1.5 rounded-full ${size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm"} text-foreground-muted font-medium`}
    >
      <span
        className="inline-block h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: PLATFORM_COLORS[platform] }}
        aria-hidden="true"
      />
      {PLATFORM_LABELS[platform]}
    </span>
  );
}

export { PLATFORM_COLORS, PLATFORM_LABELS };
