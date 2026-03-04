"use client";

import { useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import { X, AlertCircle, AlertTriangle, Info } from "lucide-react";
import type { RenderingResult } from "@/types/rendering";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: RenderingResult | null;
  clientName: string;
}

function severityIcon(severity: string) {
  switch (severity) {
    case "critical":
      return <AlertCircle className="h-4 w-4 text-status-danger" />;
    case "major":
      return <AlertTriangle className="h-4 w-4 text-status-warning" />;
    default:
      return <Info className="h-4 w-4 text-foreground-muted" />;
  }
}

function statusLabel(status: string) {
  const styles: Record<string, string> = {
    pass: "bg-badge-success-bg text-badge-success-text",
    warning: "bg-badge-warning-bg text-badge-warning-text",
    fail: "bg-badge-danger-bg text-badge-danger-text",
  };
  return styles[status] ?? "bg-badge-neutral-bg text-badge-neutral-text";
}

export function RenderingScreenshotDialog({ open, onOpenChange, result, clientName }: Props) {
  const t = useTranslations("renderings");
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  if (!result) return null;

  return (
    <dialog
      ref={ref}
      className="w-full max-w-[28rem] rounded-lg border border-card-border bg-card-bg p-0 shadow-xl backdrop:bg-black/50"
      onClose={() => onOpenChange(false)}
    >
      <div className="flex items-center justify-between border-b border-card-border p-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold capitalize text-foreground">{clientName}</h2>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusLabel(result.status)}`}>
            {t(result.status)}
          </span>
        </div>
        <button
          onClick={() => onOpenChange(false)}
          className="rounded p-1 text-foreground-muted hover:bg-surface-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="p-4">
        <img
          src={result.screenshot_url}
          alt={`${clientName} rendering`}
          className="w-full rounded-md border border-card-border object-contain"
        />

        <div className="mt-3 flex items-center gap-4 text-sm text-foreground-muted">
          <span>{t("loadTime")}: {result.load_time_ms}ms</span>
        </div>

        {result.issues.length > 0 ? (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-foreground">
              {t("issues")} ({result.issues.length})
            </h3>
            <ul className="mt-2 space-y-2">
              {result.issues.map((issue, i) => (
                <li key={i} className="flex items-start gap-2 rounded-md border border-card-border/50 p-2">
                  {severityIcon(issue.severity)}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-foreground">{issue.description}</p>
                    <p className="text-xs text-foreground-muted">{issue.affected_area}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="mt-4 text-sm text-foreground-muted">{t("noIssues")}</p>
        )}

        <p className="mt-4 text-xs text-foreground-muted/60">{t("demoNote")}</p>
      </div>
    </dialog>
  );
}
