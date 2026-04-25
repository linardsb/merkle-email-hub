"use client";

import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <h1 className="text-foreground-muted text-6xl font-bold">404</h1>
      <p className="text-foreground-muted mt-4 text-lg">
        {"The page you're looking for doesn't exist or has been moved."}
      </p>
      <Link
        href="/"
        className="bg-interactive text-foreground-inverse hover:bg-interactive-hover mt-6 rounded-md px-4 py-2 text-sm font-medium transition-colors"
      >
        {"Back to Dashboard"}
      </Link>
    </div>
  );
}
