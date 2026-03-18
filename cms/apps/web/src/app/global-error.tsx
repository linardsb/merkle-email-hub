"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="bg-surface text-foreground antialiased">
        <div className="flex min-h-screen flex-col items-center justify-center text-center p-6">
          <h1 className="text-2xl font-semibold">Application Error</h1>
          <p className="mt-2 text-foreground-muted">
            A critical error occurred. Please reload the page.
          </p>
          <button
            type="button"
            onClick={reset}
            className="mt-6 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
          >
            Reload Page
          </button>
        </div>
      </body>
    </html>
  );
}
