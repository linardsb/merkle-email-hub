"use client";

import { useTranslations } from "next-intl";

interface CompatibilityBadgeProps {
  badge: string | null | undefined;
  className?: string;
}

const BADGE_STYLES: Record<string, string> = {
  full: "bg-badge-success-bg text-badge-success-text",
  partial: "bg-badge-warning-bg text-badge-warning-text",
  issues: "bg-badge-danger-bg text-badge-danger-text",
};

export function CompatibilityBadge({ badge, className = "" }: CompatibilityBadgeProps) {
  const t = useTranslations("components");

  if (!badge) return null;

  const style = BADGE_STYLES[badge] ?? "bg-badge-default-bg text-badge-default-text";
  const labelKey = badge === "full" ? "badgeFull" : badge === "partial" ? "badgePartial" : "badgeIssues";

  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style} ${className}`}>
      {t(labelKey)}
    </span>
  );
}
