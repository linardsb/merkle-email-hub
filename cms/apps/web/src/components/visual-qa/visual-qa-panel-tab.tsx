"use client";

import { useState } from "react";
import { Camera, Eye } from "lucide-react";
import { VisualQADialog } from "./visual-qa-dialog";
import type { VisualQAEntityType } from "@/types/rendering";

interface VisualQAPanelTabProps {
  html: string;
  entityType: VisualQAEntityType;
  entityId: number;
}

export function VisualQAPanelTab({
  html,
  entityType,
  entityId,
}: VisualQAPanelTabProps) {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <>
      <div className="rounded-lg bg-surface-muted p-3">
        <div className="mb-2 flex items-center gap-2">
          <Camera className="h-4 w-4 text-foreground-muted" />
          <h3 className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
            {"Visual QA"}
          </h3>
        </div>

        <p className="mb-3 text-xs text-foreground-muted">
          {"Compare screenshots across email clients"}
        </p>

        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          disabled={!html}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          <Eye className="h-3.5 w-3.5" />
          {"View Visual QA"}
        </button>
      </div>

      <VisualQADialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        html={html}
        entityType={entityType}
        entityId={entityId}
      />
    </>
  );
}
