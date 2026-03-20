"use client";

import { useCallback, useRef, useState } from "react";
import { authFetch } from "@/lib/auth-fetch";

type ImportState = "idle" | "analyzing" | "done" | "error";

interface ImportResult {
  annotated_html: string;
  sections: Array<{
    section_id: string;
    component_name: string;
    element_selector: string;
    layout_type: string;
  }>;
  warnings: string[];
}

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
  onAccept: (annotatedHtml: string) => void;
}

const ESP_PLATFORMS = [
  { value: "", label: "Auto-detect" },
  { value: "braze", label: "Braze" },
  { value: "sfmc", label: "Salesforce Marketing Cloud" },
  { value: "klaviyo", label: "Klaviyo" },
  { value: "mailchimp", label: "Mailchimp" },
  { value: "hubspot", label: "HubSpot" },
  { value: "adobe_campaign", label: "Adobe Campaign" },
  { value: "iterable", label: "Iterable" },
] as const;

export function ImportDialog({ open, onClose, onAccept }: ImportDialogProps) {
  const [html, setHtml] = useState("");
  const [espPlatform, setEspPlatform] = useState("");
  const [state, setState] = useState<ImportState>("idle");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.size > 2 * 1024 * 1024) {
        setError("File exceeds 2MB limit");
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        setHtml(reader.result as string);
        setError(null);
      };
      reader.readAsText(file);
    },
    []
  );

  const handleImport = useCallback(async () => {
    if (html.length < 10) {
      setError("HTML must be at least 10 characters");
      return;
    }

    setState("analyzing");
    setError(null);

    try {
      const res = await authFetch("/api/v1/email/import-annotate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          html,
          esp_platform: espPlatform || null,
        }),
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: "Import failed" }));
        throw new Error(errBody.detail || `Import failed (${res.status})`);
      }

      const data: ImportResult = await res.json();

      setResult(data);
      setState("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
      setState("error");
    }
  }, [html, espPlatform]);

  const handleAccept = useCallback(() => {
    if (result) {
      onAccept(result.annotated_html);
      // Reset state
      setHtml("");
      setResult(null);
      setState("idle");
      onClose();
    }
  }, [result, onAccept, onClose]);

  const handleCancel = useCallback(() => {
    setHtml("");
    setResult(null);
    setState("idle");
    setError(null);
    onClose();
  }, [onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="w-[28rem] rounded-lg border border-border bg-card shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold text-foreground">Import HTML</h2>
          <button
            onClick={handleCancel}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Close"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="space-y-3 p-4">
          {state === "idle" || state === "error" ? (
            <>
              {/* Textarea */}
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Paste email HTML
                </label>
                <textarea
                  value={html}
                  onChange={(e) => setHtml(e.target.value)}
                  placeholder="<!DOCTYPE html>..."
                  className="h-40 w-full resize-none rounded-md border border-input bg-background px-3 py-2 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>

              {/* File upload */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">or</span>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="rounded-md border border-input px-3 py-1 text-xs text-foreground hover:bg-accent"
                >
                  Upload .html file
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".html,.htm"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </div>

              {/* ESP Platform */}
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  ESP Platform (optional)
                </label>
                <select
                  value={espPlatform}
                  onChange={(e) => setEspPlatform(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  {ESP_PLATFORMS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Error */}
              {error && (
                <p className="text-xs text-destructive">{error}</p>
              )}
            </>
          ) : state === "analyzing" ? (
            <div className="flex flex-col items-center gap-2 py-8">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <p className="text-xs text-muted-foreground">
                Analyzing email structure...
              </p>
            </div>
          ) : state === "done" && result ? (
            <div className="space-y-3">
              <div className="rounded-md border border-border bg-muted/50 p-3">
                <p className="text-sm font-medium text-foreground">
                  {result.sections.length} section{result.sections.length !== 1 ? "s" : ""} detected
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {result.sections.map((s) => (
                    <span
                      key={s.section_id}
                      className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary"
                    >
                      {s.component_name}
                      {s.layout_type === "columns" ? " (columns)" : ""}
                    </span>
                  ))}
                </div>
              </div>

              {/* Warnings */}
              {result.warnings.length > 0 && (
                <div className="rounded-md border border-warning/30 bg-warning/5 p-3">
                  <p className="mb-1 text-xs font-medium text-warning-foreground">Warnings</p>
                  <ul className="space-y-1">
                    {result.warnings.map((w, i) => (
                      <li key={i} className="text-[10px] text-muted-foreground">{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-3">
          <button
            onClick={handleCancel}
            className="rounded-md border border-input px-3 py-1.5 text-xs text-foreground hover:bg-accent"
          >
            Cancel
          </button>
          {state === "done" ? (
            <button
              onClick={handleAccept}
              className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90"
            >
              Accept
            </button>
          ) : (
            <button
              onClick={handleImport}
              disabled={state === "analyzing" || html.length < 10}
              className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Import
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
