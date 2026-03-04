"use client";

import { useTranslations } from "next-intl";
import { TranslationTable } from "@/components/settings/translation-table";

export default function TranslationsPage() {
  const t = useTranslations("translations");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>
      <TranslationTable />
    </div>
  );
}
