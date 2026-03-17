"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Zap, ChevronDown, ChevronUp, Loader2, Wrench } from "lucide-react";
import { useChaosTest } from "@/hooks/use-chaos-test";
import { useQARun } from "@/hooks/use-qa";
import type { ChaosProfileResult, ChaosFailure } from "@/types/chaos";

interface ChaosTestPanelProps {
  html: string;
}

function scoreColor(score: number): string {
  if (score >= 0.8) return "bg-status-success";
  if (score >= 0.5) return "bg-status-warning";
  return "bg-destructive";
}

function SeverityBadge({ severity }: { severity: string }) {
  const t = useTranslations("chaosTest");
  const map: Record<string, { className: string; key: string }> = {
    error: {
      className: "bg-badge-danger-bg text-badge-danger-text",
      key: "failureSeverityError",
    },
    warning: {
      className: "bg-badge-warning-bg text-badge-warning-text",
      key: "failureSeverityWarning",
    },
    info: {
      className: "bg-surface-muted text-foreground-muted",
      key: "failureSeverityInfo",
    },
  };
  const entry = map[severity] ?? map.info!;
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${entry.className}`}
    >
      {t(entry.key)}
    </span>
  );
}

function ProfileRow({
  result,
  html,
}: {
  result: ChaosProfileResult;
  html: string;
}) {
  const t = useTranslations("chaosTest");
  const [expanded, setExpanded] = useState(false);
  const qaRun = useQARun();

  const profileKey = `profileNames.${result.profile}`;
  let profileLabel: string;
  try {
    profileLabel = t(profileKey);
  } catch {
    profileLabel = result.profile;
  }

  return (
    <div className="rounded border border-border bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-2.5 py-2 text-left text-xs"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-foreground">{profileLabel}</span>
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
              result.passed
                ? "bg-badge-success-bg text-badge-success-text"
                : "bg-badge-danger-bg text-badge-danger-text"
            }`}
          >
            {t("profileScore", { score: Math.round(result.score * 100) })}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-foreground-muted">
            {t("checksPassed", {
              passed: result.checks_passed,
              total: result.checks_total,
            })}
          </span>
          {expanded ? (
            <ChevronUp className="h-3 w-3 text-foreground-muted" />
          ) : (
            <ChevronDown className="h-3 w-3 text-foreground-muted" />
          )}
        </div>
      </button>

      {expanded && result.failures.length > 0 && (
        <div className="border-t border-border px-2.5 py-2 space-y-1.5">
          {result.failures.map((f, i) => (
            <div
              key={`${f.check_name}-${i}`}
              className="flex items-start justify-between gap-2 text-xs"
            >
              <div className="flex-1">
                <div className="flex items-center gap-1.5">
                  <SeverityBadge severity={f.severity} />
                  <span className="font-medium text-foreground">
                    {f.check_name}
                  </span>
                </div>
                <p className="mt-0.5 text-foreground-muted">{f.description}</p>
              </div>
              <button
                type="button"
                disabled={qaRun.isMutating}
                onClick={() => qaRun.trigger({ html })}
                className="shrink-0 inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
              >
                <Wrench className="h-2.5 w-2.5" />
                {qaRun.isMutating ? t("fixRunning") : t("fixButton")}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChaosTestPanel({ html }: ChaosTestPanelProps) {
  const t = useTranslations("chaosTest");
  const { trigger, data, isMutating } = useChaosTest();

  return (
    <div className="rounded-lg bg-surface-muted p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-foreground-muted" />
          <h3 className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
            {t("title")}
          </h3>
        </div>
        <button
          type="button"
          disabled={isMutating}
          onClick={() => trigger({ html })}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          {isMutating ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              {t("running")}
            </>
          ) : (
            t("runButton")
          )}
        </button>
      </div>

      {!data && !isMutating && (
        <p className="text-xs text-foreground-muted">{t("noResults")}</p>
      )}

      {data && (
        <div className="space-y-3">
          {/* Critical failures */}
          {data.critical_failures.length > 0 && (
            <div className="rounded border border-destructive/30 bg-badge-danger-bg p-2">
              <h4 className="mb-1 text-xs font-medium text-badge-danger-text">
                {t("criticalFailures")}
              </h4>
              <ul className="space-y-1">
                {data.critical_failures.map((f: ChaosFailure, i: number) => (
                  <li
                    key={`crit-${f.check_name}-${i}`}
                    className="text-xs text-badge-danger-text"
                  >
                    <span className="font-medium">{f.profile}</span>:{" "}
                    {f.description}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Score bars */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground-muted">
                {t("resilienceScore")}
              </span>
              <span className="font-medium text-foreground">
                {Math.round(data.resilience_score * 100)}%
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full transition-all ${scoreColor(data.resilience_score)}`}
                style={{ width: `${data.resilience_score * 100}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground-muted">
                {t("originalScore")}
              </span>
              <span className="font-medium text-foreground">
                {Math.round(data.original_score * 100)}%
              </span>
            </div>

            <p className="text-xs text-foreground-muted">
              {t("profilesPassed", {
                passed: data.profile_results.filter(
                  (r: ChaosProfileResult) => r.passed
                ).length,
                total: data.profiles_tested,
              })}
            </p>
          </div>

          {/* Per-profile results */}
          <div className="space-y-1.5">
            {data.profile_results.map((r: ChaosProfileResult) => (
              <ProfileRow key={r.profile} result={r} html={html} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
