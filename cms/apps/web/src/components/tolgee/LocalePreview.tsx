"use client";

import { useState, useCallback, useMemo } from "react";
import { Loader2, AlertTriangle, ArrowRightLeft } from "../icons";
import { toast } from "sonner";
import { useLocaleBuild } from "@/hooks/use-tolgee";
import type { TolgeeLanguage, LocaleBuildResult } from "@/types/tolgee";

interface LocalePreviewProps {
  connectionId: number;
  tolgeeProjectId: number;
  templateId: number;
  languages: TolgeeLanguage[];
  onBuildResults?: (results: Map<string, LocaleBuildResult>) => void;
}

export function LocalePreview({
  connectionId,
  tolgeeProjectId,
  templateId,
  languages,
  onBuildResults,
}: LocalePreviewProps) {
  const { trigger: buildLocales, isMutating: isBuilding } = useLocaleBuild();

  const baseLanguage = languages.find((l) => l.base) ?? languages[0];
  const nonBaseLanguages = languages.filter((l) => !l.base);

  const [sourceLocale, setSourceLocale] = useState(baseLanguage?.tag ?? "en");
  const [targetLocale, setTargetLocale] = useState(
    nonBaseLanguages[0]?.tag ?? "",
  );
  const [buildResults, setBuildResults] = useState<
    Map<string, LocaleBuildResult>
  >(new Map());

  const sourceResult = buildResults.get(sourceLocale);
  const targetResult = buildResults.get(targetLocale);

  const sourceLang = useMemo(
    () => languages.find((l) => l.tag === sourceLocale),
    [languages, sourceLocale],
  );
  const targetLang = useMemo(
    () => languages.find((l) => l.tag === targetLocale),
    [languages, targetLocale],
  );

  const handleBuild = useCallback(
    async (locales: string[]) => {
      if (locales.length === 0) return;
      try {
        const response = await buildLocales({
          connection_id: connectionId,
          template_id: templateId,
          tolgee_project_id: tolgeeProjectId,
          locales,
        });
        const next = new Map(buildResults);
        for (const result of response.results) {
          next.set(result.locale, result);
        }
        setBuildResults(next);
        onBuildResults?.(next);
        toast.success(
          `Built ${response.results.length} locale(s) in ${Math.round(response.total_build_time_ms)}ms`,
        );
      } catch {
        toast.error("Locale build failed");
      }
    },
    [connectionId, templateId, tolgeeProjectId, buildLocales, buildResults, onBuildResults],
  );

  const handleBuildAll = useCallback(() => {
    handleBuild(languages.map((l) => l.tag));
  }, [languages, handleBuild]);

  const handleBuildPair = useCallback(() => {
    const locales = new Set([sourceLocale, targetLocale].filter(Boolean));
    handleBuild([...locales]);
  }, [sourceLocale, targetLocale, handleBuild]);

  const selectClass =
    "rounded-md border border-input-border bg-input-bg px-2 py-1 text-xs text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus";

  return (
    <div className="flex h-full flex-col">
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        {/* Source selector */}
        <select
          value={sourceLocale}
          onChange={(e) => setSourceLocale(e.target.value)}
          className={selectClass}
        >
          {languages.map((lang) => (
            <option key={lang.tag} value={lang.tag}>
              {lang.flag_emoji} {lang.name}
              {lang.base ? " (Base)" : ""}
            </option>
          ))}
        </select>

        <ArrowRightLeft className="h-3.5 w-3.5 text-foreground-muted" />

        {/* Target selector */}
        <select
          value={targetLocale}
          onChange={(e) => setTargetLocale(e.target.value)}
          className={selectClass}
        >
          {nonBaseLanguages.length === 0 ? (
            <option value="">{"No target languages"}</option>
          ) : (
            nonBaseLanguages.map((lang) => (
              <option key={lang.tag} value={lang.tag}>
                {lang.flag_emoji} {lang.name}
              </option>
            ))
          )}
        </select>

        <div className="mx-2 h-4 w-px bg-border" />

        <button
          type="button"
          onClick={handleBuildPair}
          disabled={isBuilding || !targetLocale}
          className="flex items-center gap-1.5 rounded-md bg-interactive px-2.5 py-1.5 text-xs font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
        >
          {isBuilding ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : null}
          {"Build Pair"}
        </button>

        <button
          type="button"
          onClick={handleBuildAll}
          disabled={isBuilding}
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          {"Build All"}
        </button>
      </div>

      {/* ── Preview Split ── */}
      <div className="grid flex-1 grid-cols-2 divide-x divide-border overflow-hidden">
        {/* Source */}
        <div className="flex flex-col overflow-hidden">
          <div className="flex items-center gap-2 border-b border-border px-3 py-1.5">
            <span className="text-xs font-medium text-foreground">
              {sourceLang?.flag_emoji}{" "}
              {sourceLang?.name ?? sourceLocale}
            </span>
            {sourceResult && (
              <PreviewBadges result={sourceResult} />
            )}
          </div>
          <div className="flex-1 overflow-auto bg-surface-inset">
            {sourceResult ? (
              <iframe
                srcDoc={sourceResult.html}
                sandbox=""
                title={`${sourceLocale} preview`}
                className="h-full w-full border-0 bg-white"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-foreground-muted">
                {"Click \"Build\" to generate preview"}
              </div>
            )}
          </div>
        </div>

        {/* Target */}
        <div className="flex flex-col overflow-hidden">
          <div className="flex items-center gap-2 border-b border-border px-3 py-1.5">
            <span className="text-xs font-medium text-foreground">
              {targetLang?.flag_emoji}{" "}
              {targetLang?.name ?? targetLocale}
            </span>
            {targetResult && (
              <PreviewBadges result={targetResult} />
            )}
          </div>
          <div className="flex-1 overflow-auto bg-surface-inset">
            {targetResult ? (
              <iframe
                srcDoc={targetResult.html}
                sandbox=""
                title={`${targetLocale} preview`}
                className="h-full w-full border-0 bg-white"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-foreground-muted">
                {"Click \"Build\" to generate preview"}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PreviewBadges({ result }: { result: LocaleBuildResult }) {
  return (
    <span className="flex items-center gap-1.5">
      {result.text_direction === "rtl" && (
        <span className="rounded bg-interactive/15 px-1.5 py-0.5 text-[10px] font-medium text-interactive">
          {"RTL"}
        </span>
      )}
      {result.gmail_clipping_warning && (
        <span className="flex items-center gap-0.5 rounded bg-status-danger/15 px-1.5 py-0.5 text-[10px] font-medium text-status-danger">
          <AlertTriangle className="h-3 w-3" />
          {"Clipping"}
        </span>
      )}
      <span className="text-[10px] tabular-nums text-foreground-muted">
        {Math.round(result.build_time_ms)}ms
      </span>
    </span>
  );
}
