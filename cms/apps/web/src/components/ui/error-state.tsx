"use client";

import { AlertTriangle } from "../icons";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

export function ErrorState({
  message,
  onRetry,
  retryLabel = "Try again",
  className,
}: ErrorStateProps) {
  return (
    <div
      className={`border-card-border bg-card-bg rounded-lg border px-4 py-12 text-center ${className ?? ""}`}
    >
      <AlertTriangle className="text-status-danger mx-auto h-10 w-10" />
      <p className="text-foreground-muted mt-3 text-sm">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="text-interactive mt-3 text-sm hover:underline"
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}
