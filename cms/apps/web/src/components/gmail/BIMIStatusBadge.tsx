"use client";

import { useState } from "react";
import { Loader2, Check, X, Copy } from "../icons";
import { useBIMICheck } from "@/hooks/use-gmail-intelligence";

const CHECKLIST_ITEMS = [
  "dmarcStatus",
  "bimiRecord",
  "svgValidation",
  "cmcStatus",
] as const;

const CHECKLIST_LABELS: Record<(typeof CHECKLIST_ITEMS)[number], string> = {
  dmarcStatus: "DMARC Status",
  bimiRecord: "BIMI Record",
  svgValidation: "SVG Validation",
  cmcStatus: "CMC Status",
};

function statusForItem(
  item: (typeof CHECKLIST_ITEMS)[number],
  data: NonNullable<ReturnType<typeof useBIMICheck>["data"]>,
): boolean {
  switch (item) {
    case "dmarcStatus":
      return data.dmarc_ready;
    case "bimiRecord":
      return data.bimi_record_exists;
    case "svgValidation":
      return data.svg_valid === true;
    case "cmcStatus":
      return data.cmc_status === "present";
  }
}

function extraInfo(
  item: (typeof CHECKLIST_ITEMS)[number],
  data: NonNullable<ReturnType<typeof useBIMICheck>["data"]>,
): string | null {
  switch (item) {
    case "dmarcStatus":
      return data.dmarc_policy;
    case "cmcStatus":
      return data.cmc_status;
    default:
      return null;
  }
}

export function BIMIStatusBadge() {
  const { trigger, data, isMutating, error } = useBIMICheck();
  const [domain, setDomain] = useState("");
  const [copied, setCopied] = useState(false);

  function handleCheck() {
    if (domain.trim()) {
      trigger({ domain: domain.trim() });
    }
  }

  function handleCopy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-2.5">
      {/* Domain input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder={"example.com"}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleCheck();
          }}
          className="flex-1 rounded-md border border-border bg-surface-muted px-2.5 py-1.5 text-xs text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-1 focus:ring-accent-primary"
        />
        <button
          type="button"
          disabled={isMutating || !domain.trim()}
          onClick={handleCheck}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          {isMutating ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              {"Checking…"}
            </>
          ) : (
            "Check BIMI"
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <p className="text-xs text-status-error">{error.message}</p>
      )}

      {data && (
        <div className="space-y-2">
          {/* Ready badge */}
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${
              data.ready
                ? "bg-badge-success-bg text-badge-success-text"
                : "bg-badge-danger-bg text-badge-danger-text"
            }`}
          >
            {data.ready ? "BIMI Ready" : "Not Ready"}
          </span>

          {/* 4-item checklist */}
          <div className="space-y-1">
            {CHECKLIST_ITEMS.map((item) => {
              const ok = statusForItem(item, data);
              const info = extraInfo(item, data);
              return (
                <div key={item} className="flex items-center gap-2 text-xs">
                  {ok ? (
                    <Check className="h-3.5 w-3.5 text-status-success" />
                  ) : (
                    <X className="h-3.5 w-3.5 text-status-error" />
                  )}
                  <span className="text-foreground">{CHECKLIST_LABELS[item]}</span>
                  {info && (
                    <span className="rounded bg-surface-muted px-1.5 py-0.5 text-[10px] text-foreground-muted">
                      {info}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Issues */}
          {data.issues.length > 0 && (
            <div className="space-y-0.5">
              <h4 className="text-[10px] font-medium text-foreground-muted">
                {"Issues"}
              </h4>
              {data.issues.map((issue, i) => (
                <p key={i} className="text-[10px] text-status-error">
                  {issue}
                </p>
              ))}
            </div>
          )}

          {/* Generated TXT record */}
          {data.generated_record && (
            <div>
              <h4 className="mb-1 text-[10px] font-medium text-foreground-muted">
                {"Recommended TXT Record"}
              </h4>
              <div className="flex items-start gap-1.5">
                <code className="block flex-1 overflow-x-auto rounded bg-surface-muted p-2 font-mono text-[10px] text-foreground-muted">
                  {data.generated_record}
                </code>
                <button
                  type="button"
                  onClick={() => handleCopy(data.generated_record)}
                  className="shrink-0 rounded border border-border bg-card p-1 text-foreground-muted transition-colors hover:bg-surface-hover"
                  title={"Copy"}
                >
                  <Copy className="h-3 w-3" />
                </button>
              </div>
              {copied && (
                <p className="mt-0.5 text-[10px] text-status-success">
                  {"Copied!"}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
