"use client";

import { AlertTriangle } from "lucide-react";

interface ConflictResolverProps {
  hasConflict: boolean;
  conflictDescription?: string;
  onAccept: () => void;
  onRevert: () => void;
  onDismiss: () => void;
}

export function ConflictResolver({
  hasConflict,
  conflictDescription,
  onAccept,
  onRevert,
  onDismiss,
}: ConflictResolverProps) {
  if (!hasConflict) return null;

  return (
    <div className="flex items-center gap-2 border-b border-warning bg-badge-warning-bg px-3 py-1.5 text-xs">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-badge-warning-text" />
      <span className="flex-1 text-badge-warning-text">
        {conflictDescription ?? "Merge conflict detected — review the highlighted section"}
      </span>
      <button
        type="button"
        onClick={onAccept}
        className="rounded bg-interactive px-2 py-0.5 text-[10px] font-medium text-on-interactive transition-colors hover:opacity-90"
      >
        {"Accept"}
      </button>
      <button
        type="button"
        onClick={onRevert}
        className="rounded bg-muted px-2 py-0.5 text-[10px] font-medium text-foreground transition-colors hover:bg-accent"
      >
        {"Revert to mine"}
      </button>
      <button
        type="button"
        onClick={onDismiss}
        className="text-muted-foreground transition-colors hover:text-foreground"
        aria-label="Dismiss conflict"
      >
        ×
      </button>
    </div>
  );
}
