"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";

export default function NotFound() {
  const t = useTranslations("notFound");

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <h1 className="text-6xl font-bold text-foreground-muted">404</h1>
      <p className="mt-4 text-lg text-foreground-muted">{t("description")}</p>
      <Link
        href="/"
        className="mt-6 rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
      >
        {t("backToDashboard")}
      </Link>
    </div>
  );
}
