"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import { Download, Loader2 } from "../icons";
import { ESP_LABELS } from "@/types/esp-sync";
import type { ESPTemplate } from "@/types/esp-sync";

interface ESPTemplatePreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  template: ESPTemplate | null;
  onImport: (templateId: string) => void;
  importing: boolean;
}

export function ESPTemplatePreviewDialog({
  open,
  onOpenChange,
  template,
  onImport,
  importing,
}: ESPTemplatePreviewDialogProps) {
  if (!template) return null;

  const espInfo = ESP_LABELS[template.esp_type] ?? {
    label: template.esp_type,
    color: "bg-surface-muted text-foreground-muted",
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[48rem]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle>{template.name}</DialogTitle>
            <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${espInfo.color}`}>
              {espInfo.label}
            </span>
          </div>
        </DialogHeader>

        {/* Sandboxed preview iframe */}
        <iframe
          sandbox=""
          srcDoc={template.html}
          className="border-border h-[32rem] w-full rounded-md border bg-white"
          title={"Template Preview"}
        />

        {/* Footer actions */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm transition-colors"
          >
            {"Cancel"}
          </button>
          <button
            type="button"
            onClick={() => onImport(template.id)}
            disabled={importing}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {importing ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Importing…"}
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <Download className="h-4 w-4" />
                {"Import to Hub"}
              </span>
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
