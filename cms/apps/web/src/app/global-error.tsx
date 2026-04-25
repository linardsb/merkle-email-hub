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
        <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center">
          <h1 className="text-2xl font-semibold">Application Error</h1>
          <p className="text-foreground-muted mt-2">
            A critical error occurred. Please reload the page.
          </p>
          <button
            type="button"
            onClick={reset}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover mt-6 rounded-md px-4 py-2 text-sm font-medium transition-colors"
          >
            Reload Page
          </button>
        </div>
      </body>
    </html>
  );
}
