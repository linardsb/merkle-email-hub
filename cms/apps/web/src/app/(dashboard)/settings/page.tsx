"use client";

import { useTranslations } from "next-intl";
import { LocaleSelector } from "@/components/ui/locale-selector";

export default function SettingsPage() {
  const t = useTranslations("settings");

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* Language section */}
      <section className="rounded-lg border border-default bg-card p-6">
        <h2 className="text-lg font-semibold text-foreground">{t("languageTitle")}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("languageDescription")}</p>
        <div className="mt-4">
          <LocaleSelector />
        </div>
      </section>

      {/* Placeholder for future settings sections */}
      <section className="rounded-lg border border-default bg-card p-6">
        <h2 className="text-lg font-semibold text-foreground">{t("preferencesTitle")}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("preferencesDescription")}</p>
        <div className="mt-4 text-sm text-muted-foreground italic">{t("comingSoon")}</div>
      </section>
    </div>
  );
}
