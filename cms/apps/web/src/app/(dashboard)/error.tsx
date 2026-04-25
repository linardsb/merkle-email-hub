"use client";

import { useEffect } from "react";
import { AlertTriangle } from "../../components/icons";
import Link from "next/link";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <AlertTriangle className="text-status-warning h-16 w-16" />
      <h1 className="text-foreground mt-4 text-2xl font-semibold">{"Something went wrong"}</h1>
      <p className="text-foreground-muted mt-2">
        {"An unexpected error occurred. Please try again."}
      </p>
      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-4 py-2 text-sm font-medium transition-colors"
        >
          {"Try Again"}
        </button>
        <Link
          href="/"
          className="border-card-border bg-card-bg text-foreground hover:bg-surface-hover rounded-md border px-4 py-2 text-sm font-medium transition-colors"
        >
          {"Back to Dashboard"}
        </Link>
      </div>
    </div>
  );
}
