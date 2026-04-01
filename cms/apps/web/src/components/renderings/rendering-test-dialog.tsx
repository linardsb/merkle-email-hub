"use client";

import { useState, useRef, useEffect } from "react";
import { X, Loader2, CheckCircle, AlertCircle } from "../icons";
import { useRequestRendering, useRenderingTestPolling } from "@/hooks/use-renderings";
import type { RenderingTest } from "@/types/rendering";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTestSubmitted?: (test: RenderingTest) => void;
  html?: string;
}

type DialogState = "idle" | "testing" | "completed" | "error";

export function RenderingTestDialog({ open, onOpenChange, onTestSubmitted, html: htmlProp }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const { trigger } = useRequestRendering();

  const [state, setState] = useState<DialogState>("idle");
  const [htmlInput, setHtmlInput] = useState("");
  const [subject, setSubject] = useState("");
  const [submittedTestId, setSubmittedTestId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  // Poll for progress once test is submitted
  const { data: polledTest } = useRenderingTestPolling(
    state === "testing" ? submittedTestId : null,
  );

  // Transition to completed when polling shows terminal state
  useEffect(() => {
    if (!polledTest) return;
    if (polledTest.status === "complete") {
      setState("completed");
      onTestSubmitted?.(polledTest);
    } else if (polledTest.status === "failed") {
      setState("error");
      setErrorMessage("Test Failed");
    }
  }, [polledTest?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setState("idle");
      setSubmittedTestId(null);
      setHtmlInput(htmlProp ?? "");
      setSubject("");
      setErrorMessage("");
      dialog.showModal();
    }
    if (!open && dialog.open) dialog.close();
  }, [open, htmlProp]);

  const handleSubmit = async () => {
    const htmlToSend = htmlProp || htmlInput;
    if (!htmlToSend.trim()) return;

    setState("testing");
    setErrorMessage("");
    try {
      const result = await trigger({
        html: htmlToSend,
        subject: subject || undefined,
      });
      setSubmittedTestId(result.id);
      // If already complete (demo mode returns instant), transition immediately
      if (result.status === "complete") {
        setState("completed");
        onTestSubmitted?.(result);
      }
    } catch {
      setState("error");
      setErrorMessage("Failed to load rendering data");
    }
  };

  const progressPct = polledTest
    ? Math.round(((polledTest.clients_completed ?? 0) / Math.max(polledTest.clients_requested, 1)) * 100)
    : 0;

  return (
    <dialog
      ref={ref}
      className="w-full max-w-[32rem] rounded-lg border border-card-border bg-card-bg p-0 shadow-xl backdrop:bg-black/50"
      onClose={() => onOpenChange(false)}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-card-border p-4">
        <h2 className="text-lg font-semibold text-foreground">{"Request Rendering Test"}</h2>
        <button
          onClick={() => onOpenChange(false)}
          className="rounded p-1 text-foreground-muted hover:bg-surface-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="p-4">
        {state === "idle" && (
          <>
            {/* HTML input */}
            {htmlProp ? (
              <p className="mb-4 rounded border border-card-border bg-surface-muted p-3 text-sm text-foreground-muted">
                {"HTML from current workspace build"}
              </p>
            ) : (
              <div className="mb-4">
                <label className="mb-1 block text-sm font-medium text-foreground">
                  {"Email HTML"}
                </label>
                <textarea
                  value={htmlInput}
                  onChange={(e) => setHtmlInput(e.target.value)}
                  placeholder={"Paste compiled email HTML here..."}
                  rows={6}
                  className="w-full rounded border border-card-border bg-surface p-2 font-mono text-sm text-foreground placeholder:text-foreground-muted/50 focus:border-foreground-accent focus:outline-none"
                />
              </div>
            )}

            {/* Subject line */}
            <div className="mb-4">
              <label className="mb-1 block text-sm font-medium text-foreground">
                {"Subject Line"}
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder={"e.g., Your Weekly Newsletter"}
                className="w-full rounded border border-card-border bg-surface p-2 text-sm text-foreground placeholder:text-foreground-muted/50 focus:border-foreground-accent focus:outline-none"
              />
            </div>

            {/* Footer */}
            <div className="flex justify-end border-t border-card-border pt-4">
              <button
                onClick={handleSubmit}
                disabled={!(htmlProp || htmlInput.trim())}
                className="rounded bg-foreground-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {"Run Test"}
              </button>
            </div>
          </>
        )}

        {state === "testing" && (
          <div className="flex flex-col items-center gap-4 py-12">
            <Loader2 className="h-8 w-8 animate-spin text-foreground-accent" />
            {polledTest ? (
              <>
                <p className="text-sm text-foreground-muted">
                  {`${polledTest.clients_completed ?? 0}/${polledTest.clients_requested} clients complete`}
                </p>
                <div className="h-2 w-48 overflow-hidden rounded-full bg-surface-muted">
                  <div
                    className="h-full rounded-full bg-foreground-accent transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </>
            ) : (
              <p className="text-sm text-foreground-muted">{"Processing"}</p>
            )}
          </div>
        )}

        {state === "completed" && polledTest && (
          <div className="flex flex-col items-center gap-4 py-8">
            <CheckCircle className="h-8 w-8 text-status-success" />
            <p className="text-sm font-medium text-foreground">{"Test Completed"}</p>
            <p className="text-foreground-muted">
              {polledTest.clients_completed}/{polledTest.clients_requested} {"Clients"}
            </p>
            <div className="mt-2 flex justify-end">
              <button
                onClick={() => onOpenChange(false)}
                className="rounded px-4 py-2 text-sm font-medium text-foreground-muted hover:text-foreground"
              >
                {"Close"}
              </button>
            </div>
          </div>
        )}

        {state === "error" && (
          <div className="flex flex-col items-center gap-4 py-12">
            <AlertCircle className="h-8 w-8 text-status-danger" />
            <p className="text-sm text-foreground">{errorMessage || "Failed to load rendering data"}</p>
            <button
              onClick={handleSubmit}
              className="rounded px-4 py-2 text-sm font-medium text-foreground-accent hover:opacity-80"
            >
              {"Try again"}
            </button>
          </div>
        )}
      </div>
    </dialog>
  );
}
