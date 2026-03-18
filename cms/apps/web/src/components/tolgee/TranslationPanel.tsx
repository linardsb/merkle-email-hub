"use client";

import { useState, useMemo, useCallback } from "react";
import {
  RefreshCw,
  Download,
  Search,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { useSyncKeys, usePullTranslations } from "@/hooks/use-tolgee";
import type {
  TolgeeLanguage,
  TranslationKeyRow,
  TranslationStatus,
  TranslationPullResponse,
} from "@/types/tolgee";

interface TranslationPanelProps {
  connectionId: number;
  tolgeeProjectId: number;
  templateId: number;
  languages: TolgeeLanguage[];
  onTranslationEdit?: (key: string, locale: string, value: string) => void;
}

type StatusFilter = "all" | "untranslated" | "machine-translated";

function deriveStatus(
  key: string,
  locale: string,
  translations: Record<string, string>,
): TranslationStatus {
  const value = translations[key];
  if (!value || value.trim().length === 0) return "untranslated";
  return "translated";
}

function buildKeyRows(
  syncedKeys: Record<string, string> | null,
  pullResults: TranslationPullResponse[] | null,
  languages: TolgeeLanguage[],
): TranslationKeyRow[] {
  if (!syncedKeys) return [];

  return Object.entries(syncedKeys).map(([key, sourceText]) => {
    const statuses: Record<string, TranslationStatus> = {};
    const translations: Record<string, string> = {};

    for (const lang of languages) {
      if (lang.base) continue;
      const pull = pullResults?.find((pr) => pr.locale === lang.tag);
      const translated = pull?.translations[key] ?? "";
      translations[lang.tag] = translated;
      statuses[lang.tag] = deriveStatus(key, lang.tag, pull?.translations ?? {});
    }

    return { key, sourceText, statuses, translations };
  });
}

const FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "untranslated", label: "Untranslated" },
  { value: "machine-translated", label: "Machine" },
];

const STATUS_BADGE: Record<TranslationStatus, { label: string; className: string }> = {
  translated: { label: "Done", className: "bg-status-success/15 text-status-success" },
  untranslated: { label: "Missing", className: "bg-status-danger/15 text-status-danger" },
  "machine-translated": { label: "MT", className: "bg-status-warning/15 text-status-warning" },
};

export function TranslationPanel({
  connectionId,
  tolgeeProjectId,
  templateId,
  languages,
  onTranslationEdit,
}: TranslationPanelProps) {
  const { trigger: syncKeys, isMutating: isSyncing } = useSyncKeys();
  const { trigger: pullTranslations, isMutating: isPulling } =
    usePullTranslations();

  const [syncedKeys, setSyncedKeys] = useState<Record<string, string> | null>(
    null,
  );
  const [pullResults, setPullResults] = useState<
    TranslationPullResponse[] | null
  >(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [editingCell, setEditingCell] = useState<{
    key: string;
    locale: string;
  } | null>(null);
  const [editValue, setEditValue] = useState("");

  const nonBaseLanguages = useMemo(
    () => languages.filter((l) => !l.base),
    [languages],
  );

  const keyRows = useMemo(
    () => buildKeyRows(syncedKeys, pullResults, languages),
    [syncedKeys, pullResults, languages],
  );

  const filteredRows = useMemo(() => {
    let rows = keyRows;

    if (statusFilter !== "all") {
      rows = rows.filter((row) =>
        Object.values(row.statuses).some((s) => s === statusFilter),
      );
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      rows = rows.filter(
        (row) =>
          row.key.toLowerCase().includes(q) ||
          row.sourceText.toLowerCase().includes(q),
      );
    }

    return rows;
  }, [keyRows, statusFilter, searchQuery]);

  // Progress per locale
  const localeProgress = useMemo(() => {
    const result: Record<string, { translated: number; total: number }> = {};
    for (const lang of nonBaseLanguages) {
      let translated = 0;
      for (const row of keyRows) {
        if (row.statuses[lang.tag] === "translated") translated++;
      }
      result[lang.tag] = { translated, total: keyRows.length };
    }
    return result;
  }, [keyRows, nonBaseLanguages]);

  const handleSync = useCallback(async () => {
    try {
      const result = await syncKeys({
        connection_id: connectionId,
        template_id: templateId,
      });
      toast.success(
        `Synced ${result.keys_extracted} keys (${result.push_result.created} new, ${result.push_result.updated} updated)`,
      );

      // Pull all locales (including base) in a single request
      const baseLocale = languages.find((l) => l.base);
      const allTags = languages.map((l) => l.tag);
      if (allTags.length > 0) {
        const pulls = await pullTranslations({
          connection_id: connectionId,
          tolgee_project_id: tolgeeProjectId,
          locales: allTags,
        });

        // Extract base language translations as the source key map
        if (baseLocale) {
          const basePull = pulls.find((p) => p.locale === baseLocale.tag);
          if (basePull) {
            setSyncedKeys(basePull.translations);
          }
        }

        // Store non-base translations for the table
        setPullResults(pulls.filter((p) => p.locale !== baseLocale?.tag));
      }
    } catch {
      toast.error("Failed to sync translation keys");
    }
  }, [
    connectionId,
    templateId,
    tolgeeProjectId,
    languages,
    syncKeys,
    pullTranslations,
  ]);

  const handlePull = useCallback(async () => {
    try {
      const locales = nonBaseLanguages.map((l) => l.tag);
      if (locales.length === 0) return;
      const pulls = await pullTranslations({
        connection_id: connectionId,
        tolgee_project_id: tolgeeProjectId,
        locales,
      });
      setPullResults(pulls);
      toast.success("Translations updated");
    } catch {
      toast.error("Failed to pull translations");
    }
  }, [connectionId, tolgeeProjectId, nonBaseLanguages, pullTranslations]);

  const handleEditStart = (key: string, locale: string, currentValue: string) => {
    setEditingCell({ key, locale });
    setEditValue(currentValue);
  };

  const handleEditSave = () => {
    if (!editingCell) return;
    onTranslationEdit?.(editingCell.key, editingCell.locale, editValue);
    setEditingCell(null);
    setEditValue("");
  };

  const handleEditCancel = () => {
    setEditingCell(null);
    setEditValue("");
  };

  const isLoading = isSyncing || isPulling;

  return (
    <div className="flex h-full flex-col">
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <button
          type="button"
          onClick={handleSync}
          disabled={isLoading}
          className="flex items-center gap-1.5 rounded-md bg-interactive px-2.5 py-1.5 text-xs font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
        >
          {isSyncing ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          {"Sync Keys"}
        </button>

        <button
          type="button"
          onClick={handlePull}
          disabled={isLoading || !syncedKeys}
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          {isPulling ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5" />
          )}
          {"Pull Latest"}
        </button>

        <div className="mx-2 h-4 w-px bg-border" />

        {/* Status filter */}
        <div className="flex gap-1">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setStatusFilter(opt.value)}
              className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                statusFilter === opt.value
                  ? "bg-interactive text-foreground-inverse"
                  : "text-foreground-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-foreground-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search keys…"
            className="w-48 rounded-md border border-input-border bg-input-bg py-1 pl-7 pr-2 text-xs text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
          />
        </div>
      </div>

      {/* ── Progress bars ── */}
      {keyRows.length > 0 && (
        <div className="flex gap-4 border-b border-border px-3 py-2">
          {nonBaseLanguages.map((lang) => {
            const prog = localeProgress[lang.tag];
            if (!prog) return null;
            const pct =
              prog.total > 0
                ? Math.round((prog.translated / prog.total) * 100)
                : 0;
            return (
              <div key={lang.tag} className="flex items-center gap-2 text-xs">
                <span className="text-foreground-muted">
                  {lang.flag_emoji} {lang.name}
                </span>
                <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-inset">
                  <div
                    className="h-full bg-status-success transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="tabular-nums text-foreground-muted">
                  {pct}%
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Table ── */}
      <div className="flex-1 overflow-auto">
        {!syncedKeys ? (
          <div className="flex h-full items-center justify-center text-sm text-foreground-muted">
            {"Click \"Sync Keys\" to extract translation keys from the template"}
          </div>
        ) : filteredRows.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-foreground-muted">
            {"No keys match the current filter"}
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 z-10 bg-surface">
              <tr className="border-b border-border">
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">
                  {"Key"}
                </th>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">
                  {"Source"}
                </th>
                {nonBaseLanguages.map((lang) => (
                  <th
                    key={lang.tag}
                    className="px-3 py-2 text-left font-medium text-foreground-muted"
                  >
                    {lang.flag_emoji} {lang.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr
                  key={row.key}
                  className="border-b border-border hover:bg-surface-hover"
                >
                  <td className="max-w-[12rem] truncate px-3 py-2 font-mono text-foreground-muted">
                    {row.key}
                  </td>
                  <td className="max-w-[16rem] truncate px-3 py-2 text-foreground">
                    {row.sourceText}
                  </td>
                  {nonBaseLanguages.map((lang) => {
                    const status = row.statuses[lang.tag] ?? "untranslated";
                    const badge = STATUS_BADGE[status];
                    const translation = row.translations[lang.tag] ?? "";
                    const isEditing =
                      editingCell?.key === row.key &&
                      editingCell?.locale === lang.tag;

                    return (
                      <td key={lang.tag} className="px-3 py-2">
                        {isEditing ? (
                          <div className="flex items-center gap-1">
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleEditSave();
                                if (e.key === "Escape") handleEditCancel();
                              }}
                              autoFocus
                              className="w-full rounded border border-input-focus bg-input-bg px-1.5 py-0.5 text-xs text-foreground focus:outline-none"
                            />
                            <button
                              type="button"
                              onClick={handleEditSave}
                              className="text-xs text-interactive hover:text-interactive-hover"
                            >
                              {"Save"}
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() =>
                              handleEditStart(row.key, lang.tag, translation)
                            }
                            className="group flex w-full items-center gap-1.5 text-left"
                          >
                            <span
                              className={`inline-block rounded px-1 py-0.5 text-[10px] font-medium ${badge.className}`}
                            >
                              {badge.label}
                            </span>
                            <span className="max-w-[10rem] truncate text-foreground group-hover:text-interactive">
                              {translation || "—"}
                            </span>
                          </button>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
