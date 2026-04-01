"use client";

import { AlertTriangle } from "../icons";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

export function ErrorState({ message, onRetry, retryLabel = "Try again", className }: ErrorStateProps) {
  return (
    <div className={`rounded-lg border border-card-border bg-card-bg px-4 py-12 text-center ${className ?? ""}`}>
      <AlertTriangle className="mx-auto h-10 w-10 text-status-danger" />
      <p className="mt-3 text-sm text-foreground-muted">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-3 text-sm text-interactive hover:underline">
          {retryLabel}
        </button>
      )}
    </div>
  );
}
