"use client";

interface CompatibilityBadgeProps {
  badge: string | null | undefined;
  className?: string;
}

const BADGE_STYLES: Record<string, string> = {
  full: "bg-badge-success-bg text-badge-success-text",
  partial: "bg-badge-warning-bg text-badge-warning-text",
  issues: "bg-badge-danger-bg text-badge-danger-text",
};

const BADGE_LABELS: Record<string, string> = {
  full: "Full Support",
  partial: "Partial",
  issues: "Issues",
};

export function CompatibilityBadge({ badge, className = "" }: CompatibilityBadgeProps) {
  if (!badge) return null;

  const style = BADGE_STYLES[badge] ?? "bg-badge-default-bg text-badge-default-text";

  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style} ${className}`}>
      {BADGE_LABELS[badge] ?? badge}
    </span>
  );
}
