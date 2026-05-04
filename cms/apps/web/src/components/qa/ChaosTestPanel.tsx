"use client";

import { useState } from "react";
import { Zap, ChevronDown, ChevronUp, Loader2, Wrench } from "../icons";
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
  const map: Record<string, { className: string; label: string }> = {
    error: {
      className: "bg-badge-danger-bg text-badge-danger-text",
      label: "Error",
    },
    warning: {
      className: "bg-badge-warning-bg text-badge-warning-text",
      label: "Warning",
    },
    info: {
      className: "bg-surface-muted text-foreground-muted",
      label: "Info",
    },
  };
  const entry = map[severity] ?? map.info!;
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${entry.className}`}
    >
      {entry.label}
    </span>
  );
}

function ProfileRow({ result, html }: { result: ChaosProfileResult; html: string }) {
  const [expanded, setExpanded] = useState(false);
  const qaRun = useQARun();

  const PROFILE_NAMES: Record<string, string> = {
    images_off: "Images Off",
    no_css: "No CSS",
    no_javascript: "No JavaScript",
    dark_mode: "Dark Mode",
    high_contrast: "High Contrast",
    low_bandwidth: "Low Bandwidth",
    outlook_word: "Outlook (Word)",
    gmail_clipping: "Gmail Clipping",
    yahoo_stripping: "Yahoo Stripping",
  };
  const profileLabel = PROFILE_NAMES[result.profile] ?? result.profile;

  return (
    <div className="border-border bg-card rounded border">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-2.5 py-2 text-left text-xs"
      >
        <div className="flex items-center gap-2">
          <span className="text-foreground font-medium">{profileLabel}</span>
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
              result.passed
                ? "bg-badge-success-bg text-badge-success-text"
                : "bg-badge-danger-bg text-badge-danger-text"
            }`}
          >
            {`Score: ${Math.round(result.score * 100)}%`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-foreground-muted">
            {`${result.checks_passed}/${result.checks_total} checks`}
          </span>
          {expanded ? (
            <ChevronUp className="text-foreground-muted h-3 w-3" />
          ) : (
            <ChevronDown className="text-foreground-muted h-3 w-3" />
          )}
        </div>
      </button>

      {expanded && (result.failures ?? []).length > 0 && (
        <div className="border-border space-y-1.5 border-t px-2.5 py-2">
          {(result.failures ?? []).map((f, i) => (
            <div
              key={`${f.check_name}-${i}`}
              className="flex items-start justify-between gap-2 text-xs"
            >
              <div className="flex-1">
                <div className="flex items-center gap-1.5">
                  <SeverityBadge severity={f.severity} />
                  <span className="text-foreground font-medium">{f.check_name}</span>
                </div>
                <p className="text-foreground-muted mt-0.5">{f.description}</p>
              </div>
              <button
                type="button"
                disabled={qaRun.isMutating}
                onClick={() => qaRun.trigger({ html })}
                className="border-border text-foreground hover:bg-surface-hover inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium transition-colors disabled:opacity-50"
              >
                <Wrench className="h-2.5 w-2.5" />
                {qaRun.isMutating ? "Fixing…" : "Fix"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChaosTestPanel({ html }: ChaosTestPanelProps) {
  const { trigger, data, isMutating } = useChaosTest();

  return (
    <div className="bg-surface-muted rounded-lg p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="text-foreground-muted h-4 w-4" />
          <h3 className="text-foreground-muted text-xs font-medium tracking-wider uppercase">
            {"Chaos Testing"}
          </h3>
        </div>
        <button
          type="button"
          disabled={isMutating}
          onClick={() => trigger({ html })}
          className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
        >
          {isMutating ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              {"Testing resilience…"}
            </>
          ) : (
            "Run Chaos Test"
          )}
        </button>
      </div>

      {!data && !isMutating && (
        <p className="text-foreground-muted text-xs">
          {"Run a chaos test to measure email resilience across client degradations"}
        </p>
      )}

      {data && (
        <div className="space-y-3">
          {/* Critical failures */}
          {(data.critical_failures ?? []).length > 0 && (
            <div className="border-destructive/30 bg-badge-danger-bg rounded border p-2">
              <h4 className="text-badge-danger-text mb-1 text-xs font-medium">
                {"Critical Failures"}
              </h4>
              <ul className="space-y-1">
                {(data.critical_failures ?? []).map((f: ChaosFailure, i: number) => (
                  <li key={`crit-${f.check_name}-${i}`} className="text-badge-danger-text text-xs">
                    <span className="font-medium">{f.profile}</span>: {f.description}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Score bars */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground-muted">{"Resilience Score"}</span>
              <span className="text-foreground font-medium">
                {Math.round(data.resilience_score * 100)}%
              </span>
            </div>
            <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
              <div
                className={`h-full rounded-full transition-all ${scoreColor(data.resilience_score)}`}
                style={{ width: `${data.resilience_score * 100}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground-muted">{"Original Score"}</span>
              <span className="text-foreground font-medium">
                {Math.round(data.original_score * 100)}%
              </span>
            </div>

            <p className="text-foreground-muted text-xs">
              {`${
                (data.profile_results ?? []).filter((r: ChaosProfileResult) => r.passed).length
              } of ${data.profiles_tested} profiles passed`}
            </p>
          </div>

          {/* Per-profile results */}
          <div className="space-y-1.5">
            {(data.profile_results ?? []).map((r: ChaosProfileResult) => (
              <ProfileRow key={r.profile} result={r} html={html} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
