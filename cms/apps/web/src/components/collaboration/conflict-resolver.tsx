"use client";

import { AlertTriangle } from "../icons";

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
    <div className="border-warning bg-badge-warning-bg flex items-center gap-2 border-b px-3 py-1.5 text-xs">
      <AlertTriangle className="text-badge-warning-text h-3.5 w-3.5 shrink-0" />
      <span className="text-badge-warning-text flex-1">
        {conflictDescription ?? "Merge conflict detected — review the highlighted section"}
      </span>
      <button
        type="button"
        onClick={onAccept}
        className="bg-interactive text-on-interactive rounded px-2 py-0.5 text-[10px] font-medium transition-colors hover:opacity-90"
      >
        {"Accept"}
      </button>
      <button
        type="button"
        onClick={onRevert}
        className="bg-muted text-foreground hover:bg-accent rounded px-2 py-0.5 text-[10px] font-medium transition-colors"
      >
        {"Revert to mine"}
      </button>
      <button
        type="button"
        onClick={onDismiss}
        className="text-muted-foreground hover:text-foreground transition-colors"
        aria-label="Dismiss conflict"
      >
        ×
      </button>
    </div>
  );
}
