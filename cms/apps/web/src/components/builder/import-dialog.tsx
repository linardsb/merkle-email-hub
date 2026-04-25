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

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
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
  }, []);

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
    <div className="bg-background/80 fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm">
      <div className="border-border bg-card w-[28rem] rounded-lg border shadow-lg">
        {/* Header */}
        <div className="border-border flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-foreground text-sm font-semibold">Import HTML</h2>
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
                <label className="text-muted-foreground mb-1 block text-xs font-medium">
                  Paste email HTML
                </label>
                <textarea
                  value={html}
                  onChange={(e) => setHtml(e.target.value)}
                  placeholder="<!DOCTYPE html>..."
                  className="border-input bg-background text-foreground placeholder:text-muted-foreground focus:ring-ring h-40 w-full resize-none rounded-md border px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1"
                />
              </div>

              {/* File upload */}
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-xs">or</span>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="border-input text-foreground hover:bg-accent rounded-md border px-3 py-1 text-xs"
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
                <label className="text-muted-foreground mb-1 block text-xs font-medium">
                  ESP Platform (optional)
                </label>
                <select
                  value={espPlatform}
                  onChange={(e) => setEspPlatform(e.target.value)}
                  className="border-input bg-background text-foreground focus:ring-ring w-full rounded-md border px-3 py-1.5 text-xs focus:outline-none focus:ring-1"
                >
                  {ESP_PLATFORMS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Error */}
              {error && <p className="text-destructive text-xs">{error}</p>}
            </>
          ) : state === "analyzing" ? (
            <div className="flex flex-col items-center gap-2 py-8">
              <div className="border-primary h-5 w-5 animate-spin rounded-full border-2 border-t-transparent" />
              <p className="text-muted-foreground text-xs">Analyzing email structure...</p>
            </div>
          ) : state === "done" && result ? (
            <div className="space-y-3">
              <div className="border-border bg-muted/50 rounded-md border p-3">
                <p className="text-foreground text-sm font-medium">
                  {result.sections.length} section{result.sections.length !== 1 ? "s" : ""} detected
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {result.sections.map((s) => (
                    <span
                      key={s.section_id}
                      className="bg-primary/10 text-primary rounded-full px-2 py-0.5 text-[10px] font-medium"
                    >
                      {s.component_name}
                      {s.layout_type === "columns" ? " (columns)" : ""}
                    </span>
                  ))}
                </div>
              </div>

              {/* Warnings */}
              {result.warnings.length > 0 && (
                <div className="border-warning/30 bg-warning/5 rounded-md border p-3">
                  <p className="text-warning-foreground mb-1 text-xs font-medium">Warnings</p>
                  <ul className="space-y-1">
                    {result.warnings.map((w, i) => (
                      <li key={i} className="text-muted-foreground text-[10px]">
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-border flex items-center justify-end gap-2 border-t px-4 py-3">
          <button
            onClick={handleCancel}
            className="border-input text-foreground hover:bg-accent rounded-md border px-3 py-1.5 text-xs"
          >
            Cancel
          </button>
          {state === "done" ? (
            <button
              onClick={handleAccept}
              className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-md px-3 py-1.5 text-xs"
            >
              Accept
            </button>
          ) : (
            <button
              onClick={handleImport}
              disabled={state === "analyzing" || html.length < 10}
              className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-md px-3 py-1.5 text-xs disabled:opacity-50"
            >
              Import
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
