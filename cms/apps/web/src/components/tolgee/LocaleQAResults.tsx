"use client";

import { useState, useCallback, useMemo } from "react";
import { Check, X, AlertTriangle, Clock, Loader2, Play } from "../icons";
import { toast } from "sonner";
import { authFetch, LONG_TIMEOUT_MS } from "@/lib/auth-fetch";
import { ApiError } from "@/lib/api-error";
import type {
  TolgeeLanguage,
  LocaleQAStatus,
  LocaleQASummary,
  LocaleQACheck,
  LocaleBuildResult,
} from "@/types/tolgee";

interface LocaleQAResultsProps {
  templateId: number;
  languages: TolgeeLanguage[];
  buildResults: Map<string, LocaleBuildResult>;
}

const QA_CHECKS = [
  "html_validation",
  "css_support",
  "file_size",
  "accessibility",
  "dark_mode",
  "spam_score",
  "link_validation",
  "personalisation_syntax",
] as const;

const CHECK_LABELS: Record<string, string> = {
  html_validation: "HTML",
  css_support: "CSS",
  file_size: "Size",
  accessibility: "A11y",
  dark_mode: "Dark",
  spam_score: "Spam",
  link_validation: "Links",
  personalisation_syntax: "Tokens",
};

const STATUS_ICON: Record<LocaleQAStatus, { icon: typeof Check; className: string }> = {
  pass: { icon: Check, className: "text-status-success" },
  fail: { icon: X, className: "text-status-danger" },
  warning: { icon: AlertTriangle, className: "text-status-warning" },
  pending: { icon: Clock, className: "text-foreground-muted" },
};

interface QACheckResult {
  check_name: string;
  passed: boolean;
  score: number;
  details: string | null;
  severity: string;
}

interface QAResultResponse {
  checks: QACheckResult[];
}

export function LocaleQAResults({ templateId, languages, buildResults }: LocaleQAResultsProps) {
  const [qaSummaries, setQaSummaries] = useState<Map<string, LocaleQASummary>>(new Map());
  const [isRunning, setIsRunning] = useState(false);

  const localesWithBuilds = useMemo(
    () => languages.filter((l) => buildResults.has(l.tag)),
    [languages, buildResults],
  );

  const runQAForLocale = useCallback(
    async (locale: string): Promise<LocaleQASummary> => {
      const build = buildResults.get(locale);
      if (!build) {
        return {
          locale,
          checks: QA_CHECKS.map((c) => ({ check: c, status: "pending" as const })),
          overallStatus: "pending",
        };
      }

      const res = await authFetch("/api/v1/qa/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          html: build.html,
          template_id: templateId,
        }),
        timeoutMs: LONG_TIMEOUT_MS,
      });

      if (!res.ok) {
        throw new ApiError(res.status, "QA run failed");
      }

      const result: QAResultResponse = await res.json();

      const checks: LocaleQACheck[] = QA_CHECKS.map((checkName) => {
        const check = result.checks.find((c) => c.check_name === checkName);
        if (!check) return { check: checkName, status: "pending" as const };

        let status: LocaleQAStatus = check.passed ? "pass" : "fail";

        // Gmail clipping override for file_size
        if (checkName === "file_size" && build.gmail_clipping_warning) {
          status = "fail";
        }

        // Treat warnings as warnings
        if (check.severity === "warning" && !check.passed) {
          status = "warning";
        }

        return {
          check: checkName,
          status,
          message: check.details ?? undefined,
        };
      });

      const failCount = checks.filter((c) => c.status === "fail").length;
      const warnCount = checks.filter((c) => c.status === "warning").length;
      const overallStatus: LocaleQAStatus =
        failCount > 0 ? "fail" : warnCount > 0 ? "warning" : "pass";

      return { locale, checks, overallStatus };
    },
    [buildResults, templateId],
  );

  const handleRunAll = useCallback(async () => {
    if (localesWithBuilds.length === 0) {
      toast.error("No locale builds available — build locales first");
      return;
    }

    setIsRunning(true);
    try {
      const results = await Promise.all(localesWithBuilds.map((l) => runQAForLocale(l.tag)));
      const next = new Map<string, LocaleQASummary>();
      for (const summary of results) {
        next.set(summary.locale, summary);
      }
      setQaSummaries(next);
      toast.success(`QA complete for ${results.length} locale(s)`);
    } catch {
      toast.error("Some QA runs failed");
    } finally {
      setIsRunning(false);
    }
  }, [localesWithBuilds, runQAForLocale]);

  return (
    <div className="flex flex-col">
      {/* ── Header ── */}
      <div className="border-border flex items-center gap-2 border-b px-3 py-2">
        <span className="text-foreground text-xs font-medium">{"Locale QA Matrix"}</span>
        <div className="flex-1" />
        <button
          type="button"
          onClick={handleRunAll}
          disabled={isRunning || localesWithBuilds.length === 0}
          className="bg-interactive text-foreground-inverse hover:bg-interactive-hover flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-50"
        >
          {isRunning ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          {"Run QA for All Locales"}
        </button>
      </div>

      {/* ── Matrix ── */}
      {localesWithBuilds.length === 0 ? (
        <div className="text-foreground-muted px-3 py-6 text-center text-xs">
          {"Build locales first to run QA checks"}
        </div>
      ) : (
        <div className="overflow-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-border border-b">
                <th className="text-foreground-muted px-3 py-2 text-left font-medium">{"Check"}</th>
                {localesWithBuilds.map((lang) => (
                  <th
                    key={lang.tag}
                    className="text-foreground-muted px-3 py-2 text-center font-medium"
                  >
                    {lang.flag_emoji} {lang.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {QA_CHECKS.map((checkName) => (
                <tr key={checkName} className="border-border hover:bg-surface-hover border-b">
                  <td className="text-foreground px-3 py-2 font-medium">
                    {CHECK_LABELS[checkName] ?? checkName}
                  </td>
                  {localesWithBuilds.map((lang) => {
                    const summary = qaSummaries.get(lang.tag);
                    const check = summary?.checks.find((c) => c.check === checkName);
                    const status: LocaleQAStatus = check?.status ?? "pending";
                    const { icon: Icon, className } = STATUS_ICON[status];

                    return (
                      <td key={lang.tag} className="px-3 py-2 text-center" title={check?.message}>
                        <Icon className={`mx-auto h-4 w-4 ${className}`} />
                      </td>
                    );
                  })}
                </tr>
              ))}

              {/* Overall row */}
              <tr className="border-border bg-surface-elevated border-t-2">
                <td className="text-foreground px-3 py-2 font-medium">{"Overall"}</td>
                {localesWithBuilds.map((lang) => {
                  const summary = qaSummaries.get(lang.tag);
                  const status: LocaleQAStatus = summary?.overallStatus ?? "pending";
                  const { icon: Icon, className } = STATUS_ICON[status];
                  return (
                    <td key={lang.tag} className="px-3 py-2 text-center">
                      <Icon className={`mx-auto h-4 w-4 ${className}`} />
                    </td>
                  );
                })}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
