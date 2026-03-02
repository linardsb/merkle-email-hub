import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={`rounded-lg border border-card-border bg-card-bg px-4 py-12 text-center ${className ?? ""}`}
    >
      <Icon className="mx-auto h-10 w-10 text-foreground-muted" />
      <p className="mt-3 text-sm font-medium text-foreground">{title}</p>
      {description && (
        <p className="mt-1 text-sm text-foreground-muted">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
