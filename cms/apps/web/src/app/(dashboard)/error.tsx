"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle } from "lucide-react";
import Link from "next/link";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errors");

  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <AlertTriangle className="h-16 w-16 text-status-warning" />
      <h1 className="mt-4 text-2xl font-semibold text-foreground">
        {t("title")}
      </h1>
      <p className="mt-2 text-foreground-muted">{t("description")}</p>
      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
        >
          {t("retry")}
        </button>
        <Link
          href="/"
          className="rounded-md border border-card-border bg-card-bg px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
        >
          {t("backToDashboard")}
        </Link>
      </div>
    </div>
  );
}
