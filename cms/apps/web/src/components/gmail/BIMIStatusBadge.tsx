"use client";

import { useState } from "react";
import { Loader2, Check, X, Copy } from "../icons";
import { useBIMICheck } from "@/hooks/use-gmail-intelligence";

const CHECKLIST_ITEMS = ["dmarcStatus", "bimiRecord", "svgValidation", "cmcStatus"] as const;

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
          className="border-border bg-surface-muted text-foreground placeholder:text-foreground-muted focus:ring-accent-primary flex-1 rounded-md border px-2.5 py-1.5 text-xs focus:ring-1 focus:outline-none"
        />
        <button
          type="button"
          disabled={isMutating || !domain.trim()}
          onClick={handleCheck}
          className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
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
      {error && <p className="text-status-error text-xs">{error.message}</p>}

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
                    <Check className="text-status-success h-3.5 w-3.5" />
                  ) : (
                    <X className="text-status-error h-3.5 w-3.5" />
                  )}
                  <span className="text-foreground">{CHECKLIST_LABELS[item]}</span>
                  {info && (
                    <span className="bg-surface-muted text-foreground-muted rounded px-1.5 py-0.5 text-[10px]">
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
              <h4 className="text-foreground-muted text-[10px] font-medium">{"Issues"}</h4>
              {data.issues.map((issue, i) => (
                <p key={i} className="text-status-error text-[10px]">
                  {issue}
                </p>
              ))}
            </div>
          )}

          {/* Generated TXT record */}
          {data.generated_record && (
            <div>
              <h4 className="text-foreground-muted mb-1 text-[10px] font-medium">
                {"Recommended TXT Record"}
              </h4>
              <div className="flex items-start gap-1.5">
                <code className="bg-surface-muted text-foreground-muted block flex-1 overflow-x-auto rounded p-2 font-mono text-[10px]">
                  {data.generated_record}
                </code>
                <button
                  type="button"
                  onClick={() => handleCopy(data.generated_record)}
                  className="border-border bg-card text-foreground-muted hover:bg-surface-hover shrink-0 rounded border p-1 transition-colors"
                  title={"Copy"}
                >
                  <Copy className="h-3 w-3" />
                </button>
              </div>
              {copied && <p className="text-status-success mt-0.5 text-[10px]">{"Copied!"}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
