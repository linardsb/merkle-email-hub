"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { X, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { useRenderingClients, useRequestRendering } from "@/hooks/use-renderings";
import type { RenderingProvider, RenderingTest, RenderingClientCategory } from "@/types/rendering";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTestComplete?: (test: RenderingTest) => void;
}

type DialogState = "idle" | "testing" | "completed" | "error";

export function RenderingTestDialog({ open, onOpenChange, onTestComplete }: Props) {
  const t = useTranslations("renderings");
  const ref = useRef<HTMLDialogElement>(null);
  const { data: clients } = useRenderingClients();
  const { trigger, error: mutationError } = useRequestRendering();

  const [state, setState] = useState<DialogState>("idle");
  const [provider, setProvider] = useState<RenderingProvider>("litmus");
  const [selectedClients, setSelectedClients] = useState<Set<string>>(new Set());
  const [completedTest, setCompletedTest] = useState<RenderingTest | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setState("idle");
      setCompletedTest(null);
      if (clients) setSelectedClients(new Set(clients.map((c) => c.id)));
      dialog.showModal();
    }
    if (!open && dialog.open) dialog.close();
  }, [open, clients]);

  const toggleClient = useCallback((id: string) => {
    setSelectedClients((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleCategory = useCallback((category: RenderingClientCategory) => {
    if (!clients) return;
    const catIds = clients.filter((c) => c.category === category).map((c) => c.id);
    setSelectedClients((prev) => {
      const allSelected = catIds.every((id) => prev.has(id));
      const next = new Set(prev);
      for (const id of catIds) {
        if (allSelected) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  }, [clients]);

  const handleRun = async () => {
    setState("testing");
    try {
      const result = await trigger({
        provider,
        client_ids: Array.from(selectedClients),
      });
      setCompletedTest(result);
      setState("completed");
      onTestComplete?.(result);
    } catch {
      setState("error");
    }
  };

  const categories: { key: RenderingClientCategory; label: string }[] = [
    { key: "desktop", label: t("desktop") },
    { key: "webmail", label: t("webmail") },
    { key: "mobile", label: t("mobile") },
  ];

  return (
    <dialog
      ref={ref}
      className="w-full max-w-4xl rounded-lg border border-card-border bg-card-bg p-0 shadow-xl backdrop:bg-black/50"
      onClose={() => onOpenChange(false)}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-card-border p-4">
        <h2 className="text-lg font-semibold text-foreground">{t("requestTest")}</h2>
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
            {/* Provider toggle */}
            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-foreground">{t("providerToggle")}</label>
              <div className="flex gap-1 rounded-md border border-card-border p-1">
                <button
                  className={`flex-1 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                    provider === "litmus"
                      ? "bg-foreground-accent text-white"
                      : "text-foreground-muted hover:text-foreground"
                  }`}
                  onClick={() => setProvider("litmus")}
                >
                  {t("litmus")}
                </button>
                <button
                  className={`flex-1 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                    provider === "email_on_acid"
                      ? "bg-foreground-accent text-white"
                      : "text-foreground-muted hover:text-foreground"
                  }`}
                  onClick={() => setProvider("email_on_acid")}
                >
                  {t("emailOnAcid")}
                </button>
              </div>
            </div>

            {/* Client selector */}
            <div className="max-h-[50vh] overflow-y-auto">
              {categories.map((cat) => {
                const catClients = clients?.filter((c) => c.category === cat.key) ?? [];
                const allSelected = catClients.every((c) => selectedClients.has(c.id));
                return (
                  <div key={cat.key} className="mb-3">
                    <button
                      className="mb-1 flex w-full items-center gap-2 text-left"
                      onClick={() => toggleCategory(cat.key)}
                    >
                      <input
                        type="checkbox"
                        checked={allSelected}
                        readOnly
                        className="rounded border-card-border"
                      />
                      <span className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                        {cat.label} ({catClients.length})
                      </span>
                    </button>
                    <div className="ml-6 space-y-1">
                      {catClients.map((client) => (
                        <label key={client.id} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={selectedClients.has(client.id)}
                            onChange={() => toggleClient(client.id)}
                            className="rounded border-card-border"
                          />
                          <span className="text-foreground">{client.name}</span>
                          <span className="text-xs text-foreground-muted">{client.market_share}%</span>
                        </label>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div className="mt-4 flex items-center justify-between border-t border-card-border pt-4">
              <span className="text-sm text-foreground-muted">
                {t("clientsSelected", { count: selectedClients.size })}
              </span>
              <button
                onClick={handleRun}
                disabled={selectedClients.size === 0}
                className="rounded bg-foreground-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {t("runTest")}
              </button>
            </div>
          </>
        )}

        {state === "testing" && (
          <div className="flex flex-col items-center gap-4 py-12">
            <Loader2 className="h-8 w-8 animate-spin text-foreground-accent" />
            <p className="text-sm text-foreground-muted">
              {t("running", { count: selectedClients.size })}
            </p>
          </div>
        )}

        {state === "completed" && completedTest && (
          <div>
            <div className="flex flex-col items-center gap-2 py-6">
              <CheckCircle className="h-8 w-8 text-status-success" />
              <p className="text-sm font-medium text-foreground">{t("testCompleted")}</p>
              <p className="text-3xl font-bold text-foreground">{completedTest.compatibility_score}%</p>
            </div>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-5">
              {completedTest.results.map((r) => {
                const dotColor =
                  r.status === "pass"
                    ? "bg-status-success"
                    : r.status === "warning"
                      ? "bg-status-warning"
                      : "bg-status-danger";
                return (
                  <div key={r.client_id} className="rounded-md border border-card-border/50 p-2 text-center">
                    <img
                      src={r.screenshot_url}
                      alt={r.client_id}
                      className="aspect-[3/2] w-full rounded object-cover"
                      loading="lazy"
                    />
                    <div className="mt-1 flex items-center justify-center gap-1">
                      <span className={`h-2 w-2 rounded-full ${dotColor}`} />
                      <span className="truncate text-xs capitalize text-foreground-muted">
                        {r.client_id.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => onOpenChange(false)}
                className="rounded px-4 py-2 text-sm font-medium text-foreground-muted hover:text-foreground"
              >
                {t("close")}
              </button>
            </div>
          </div>
        )}

        {state === "error" && (
          <div className="flex flex-col items-center gap-4 py-12">
            <AlertCircle className="h-8 w-8 text-status-danger" />
            <p className="text-sm text-foreground">{t("error")}</p>
            <button
              onClick={handleRun}
              className="rounded px-4 py-2 text-sm font-medium text-foreground-accent hover:opacity-80"
            >
              {t("retry")}
            </button>
          </div>
        )}
      </div>
    </dialog>
  );
}
