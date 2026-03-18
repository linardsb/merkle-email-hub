"use client";

import { useRef, useEffect } from "react";
import { X, ImageOff } from "lucide-react";
import type { ScreenshotResult } from "@/types/rendering";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: ScreenshotResult | null;
}

function statusLabel(status: string) {
  const styles: Record<string, string> = {
    complete: "bg-badge-success-bg text-badge-success-text",
    failed: "bg-badge-danger-bg text-badge-danger-text",
    pending: "bg-badge-neutral-bg text-badge-neutral-text",
  };
  return styles[status] ?? "bg-badge-neutral-bg text-badge-neutral-text";
}

export function RenderingScreenshotDialog({ open, onOpenChange, result }: Props) {
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
          <h2 className="text-lg font-semibold text-foreground">{result.client_name ?? ""}</h2>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusLabel(result.status ?? "")}`}>
            {(result.status ?? "pending").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
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
        {result.screenshot_url ? (
          <img
            src={result.screenshot_url}
            alt={`${result.client_name} rendering`}
            className="w-full rounded-md border border-card-border object-contain"
          />
        ) : (
          <div className="flex aspect-[3/2] w-full items-center justify-center rounded-md border border-card-border bg-surface-muted">
            <div className="flex flex-col items-center gap-2">
              <ImageOff className="h-8 w-8 text-foreground-muted/40" />
              <p className="text-sm text-foreground-muted">{"Screenshot not yet available"}</p>
            </div>
          </div>
        )}

        <div className="mt-3 flex items-center gap-4 text-sm text-foreground-muted">
          {result.os && <span className="capitalize">{result.os}</span>}
          {result.category && <span className="capitalize">{result.category}</span>}
        </div>

        <p className="mt-4 text-xs text-foreground-muted/60">{"Screenshots are simulated in demo mode"}</p>
      </div>
    </dialog>
  );
}
