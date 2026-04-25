import type { LucideIcon } from "../icons";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={`border-card-border bg-card-bg rounded-lg border px-4 py-12 text-center ${className ?? ""}`}
    >
      <Icon className="text-foreground-muted mx-auto h-10 w-10" />
      <p className="text-foreground mt-3 text-sm font-medium">{title}</p>
      {description && <p className="text-foreground-muted mt-1 text-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
