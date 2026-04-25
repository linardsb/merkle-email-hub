"use client";

import { useState } from "react";
import { FlaskConical, ChevronDown, ChevronUp, Loader2, Check } from "../icons";
import { usePropertyTest } from "@/hooks/use-property-test";
import type { PropertyFailureSchema } from "@/types/chaos";

const CASE_OPTIONS = [50, 100, 500] as const;

const CONFIG_DISPLAY_KEYS = [
  "section_count",
  "image_count",
  "table_nesting_depth",
  "has_mso_conditionals",
  "has_dark_mode",
  "target_size_kb",
] as const;

function FailureRow({ failure }: { failure: PropertyFailureSchema }) {
  const [expanded, setExpanded] = useState(false);
  const [showConfig, setShowConfig] = useState(false);

  return (
    <div className="border-border bg-card rounded border">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-2.5 py-2 text-left text-xs"
      >
        <div className="flex items-center gap-2">
          <span className="text-foreground font-medium">{failure.invariant_name}</span>
          <span className="bg-badge-danger-bg text-badge-danger-text rounded-full px-1.5 py-0.5 text-[10px] font-medium">
            {`${failure.violations.length} violations`}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="text-foreground-muted h-3 w-3" />
        ) : (
          <ChevronDown className="text-foreground-muted h-3 w-3" />
        )}
      </button>

      {expanded && (
        <div className="border-border space-y-2 border-t px-2.5 py-2">
          <ul className="space-y-1">
            {failure.violations.map((v, i) => (
              <li
                key={i}
                className="text-foreground-muted border-destructive/30 border-l-2 pl-2 text-xs"
              >
                {v}
              </li>
            ))}
          </ul>

          <button
            type="button"
            onClick={() => setShowConfig((v) => !v)}
            className="text-foreground-muted text-[10px] font-medium underline-offset-2 hover:underline"
          >
            {showConfig ? "Hide Config" : "Show Config"}
          </button>

          {showConfig && (
            <dl className="bg-surface-muted grid grid-cols-2 gap-x-3 gap-y-1 rounded p-2 text-[10px]">
              {CONFIG_DISPLAY_KEYS.map((key) => {
                const val = failure.config[key];
                if (val === undefined) return null;
                return (
                  <div key={key} className="contents">
                    <dt className="text-foreground-muted font-medium">{key}</dt>
                    <dd className="text-foreground">{String(val)}</dd>
                  </div>
                );
              })}
            </dl>
          )}
        </div>
      )}
    </div>
  );
}

export function PropertyTestPanel() {
  const { trigger, data, isMutating } = usePropertyTest();
  const [numCases, setNumCases] = useState(100);

  return (
    <div className="bg-surface-muted rounded-lg p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="text-foreground-muted h-4 w-4" />
          <h3 className="text-foreground-muted text-xs font-medium uppercase tracking-wider">
            {"Property Testing"}
          </h3>
        </div>
        <div className="flex items-center gap-1.5">
          <select
            value={numCases}
            onChange={(e) => setNumCases(Number(e.target.value))}
            disabled={isMutating}
            className="border-border bg-card text-foreground rounded border px-1.5 py-0.5 text-xs disabled:opacity-50"
          >
            {CASE_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={isMutating}
            onClick={() => trigger({ num_cases: numCases })}
            className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
          >
            {isMutating ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                {`Testing ${numCases} cases…`}
              </>
            ) : (
              "Run Property Test"
            )}
          </button>
        </div>
      </div>

      {!data && !isMutating && (
        <p className="text-foreground-muted text-xs">
          {"Run property tests to verify email invariants hold across random configurations"}
        </p>
      )}

      {data && (
        <div className="space-y-3">
          {/* Pass/fail gauge */}
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground-muted">{"Cases"}</span>
              <span className="text-foreground font-medium">
                {`${data.passed} of ${data.total_cases} passed (${Math.round((data.passed / data.total_cases) * 100)}%)`}
              </span>
            </div>
            <div className="bg-muted mt-1 h-2 w-full overflow-hidden rounded-full">
              <div
                className={`h-full rounded-full transition-all ${
                  data.failed === 0 ? "bg-status-success" : "bg-status-warning"
                }`}
                style={{
                  width: `${(data.passed / data.total_cases) * 100}%`,
                }}
              />
            </div>
            <p className="text-foreground-muted mt-1 font-mono text-[10px]">
              {`Seed: ${data.seed}`}
            </p>
          </div>

          {/* Invariant chips */}
          <div>
            <h4 className="text-foreground-muted mb-1 text-xs font-medium">
              {"Invariants Tested"}
            </h4>
            <div className="flex flex-wrap gap-1">
              {data.invariants_tested.map((inv: string) => {
                const hasFail = data.failures.some(
                  (f: PropertyFailureSchema) => f.invariant_name === inv,
                );
                return (
                  <span
                    key={inv}
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      hasFail
                        ? "bg-badge-danger-bg text-badge-danger-text"
                        : "bg-badge-success-bg text-badge-success-text"
                    }`}
                  >
                    {!hasFail && <Check className="h-2.5 w-2.5" />}
                    {inv}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Failures */}
          {data.failed === 0 ? (
            <p className="text-status-success text-xs font-medium">{"All invariants passed"}</p>
          ) : (
            <div className="space-y-1.5">
              <h4 className="text-foreground-muted text-xs font-medium">{"Failures"}</h4>
              {data.failures.map((f: PropertyFailureSchema, i: number) => (
                <FailureRow key={`${f.invariant_name}-${i}`} failure={f} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
