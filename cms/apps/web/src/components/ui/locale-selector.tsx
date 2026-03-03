"use client";

import { useLocale } from "@/hooks/use-locale";
import { SUPPORTED_LOCALES } from "@/lib/locales";
import { Globe } from "lucide-react";

export function LocaleSelector() {
  const { locale, setLocale } = useLocale();

  return (
    <div className="flex items-center gap-1.5">
      <Globe className="h-4 w-4 text-sidebar-text" />
      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value)}
        className="rounded border-none bg-transparent py-0.5 text-xs text-sidebar-text focus:outline-none focus:ring-1 focus:ring-interactive"
      >
        {SUPPORTED_LOCALES.map((loc) => (
          <option key={loc.code} value={loc.code}>
            {loc.nativeName}
          </option>
        ))}
      </select>
    </div>
  );
}
