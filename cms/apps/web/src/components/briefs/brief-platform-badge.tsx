"use client";

import { useTranslations } from "next-intl";
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

const PLATFORM_LABEL_KEYS: Record<BriefPlatform, string> = {
  jira: "platformJira",
  asana: "platformAsana",
  monday: "platformMonday",
  clickup: "platformClickup",
  trello: "platformTrello",
  notion: "platformNotion",
  wrike: "platformWrike",
  basecamp: "platformBasecamp",
};

interface BriefPlatformBadgeProps {
  platform: BriefPlatform;
  size?: "sm" | "md";
}

export function BriefPlatformBadge({ platform, size = "sm" }: BriefPlatformBadgeProps) {
  const t = useTranslations("briefs");

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full bg-surface-muted ${size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm"} font-medium text-foreground-muted`}>
      <span
        className="inline-block h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: PLATFORM_COLORS[platform] }}
        aria-hidden="true"
      />
      {t(PLATFORM_LABEL_KEYS[platform])}
    </span>
  );
}

export { PLATFORM_COLORS, PLATFORM_LABEL_KEYS };
