"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { SUPPORTED_LOCALES } from "@/lib/locales";
import { Search } from "lucide-react";
import type { TranslationEntry } from "@/types/locale";
import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";

export function TranslationTable() {
  const t = useTranslations("translations");
  const [search, setSearch] = useState("");
  const [nsFilter, setNsFilter] = useState<string>("all");

  const { data: entries, error } = useSWR<TranslationEntry[]>(
    "/api/v1/translations",
    fetcher,
  );

  const namespaces = useMemo(() => {
    if (!entries) return [];
    return [...new Set(entries.map((e) => e.namespace))].sort();
  }, [entries]);

  const filtered = useMemo(() => {
    if (!entries) return [];
    return entries.filter((entry) => {
      if (nsFilter !== "all" && entry.namespace !== nsFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        const matchesKey = entry.key.toLowerCase().includes(q);
        const matchesValue = Object.values(entry.values).some((v) =>
          v.toLowerCase().includes(q),
        );
        if (!matchesKey && !matchesValue) return false;
      }
      return true;
    });
  }, [entries, nsFilter, search]);

  if (error) {
    return <p className="text-sm text-destructive">{t("error")}</p>;
  }

  if (!entries) {
    return (
      <div className="animate-pulse space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-10 rounded bg-skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="h-9 rounded-md border border-default bg-input pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-interactive"
          />
        </div>
        <select
          value={nsFilter}
          onChange={(e) => setNsFilter(e.target.value)}
          className="h-9 rounded-md border border-default bg-input px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-interactive"
        >
          <option value="all">{t("allNamespaces")}</option>
          {namespaces.map((ns) => (
            <option key={ns} value={ns}>
              {ns}
            </option>
          ))}
        </select>
        <span className="text-xs text-muted-foreground">
          {t("showingCount", { count: filtered.length, total: entries.length })}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-default">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-default bg-surface-raised">
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">{t("namespace")}</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">{t("key")}</th>
              {SUPPORTED_LOCALES.map((loc) => (
                <th key={loc.code} className="px-3 py-2 text-left font-medium text-muted-foreground">
                  {loc.code.toUpperCase()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={2 + SUPPORTED_LOCALES.length}
                  className="px-3 py-8 text-center text-muted-foreground"
                >
                  {t("noResults")}
                </td>
              </tr>
            ) : (
              filtered.map((entry) => (
                <tr
                  key={`${entry.namespace}.${entry.key}`}
                  className="border-b border-default last:border-0 hover:bg-surface-raised/50"
                >
                  <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                    {entry.namespace}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-foreground">
                    {entry.key}
                  </td>
                  {SUPPORTED_LOCALES.map((loc) => (
                    <td key={loc.code} className="max-w-48 truncate px-3 py-2 text-foreground">
                      {entry.values[loc.code] || (
                        <span className="text-xs text-warning italic">{t("missing")}</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
