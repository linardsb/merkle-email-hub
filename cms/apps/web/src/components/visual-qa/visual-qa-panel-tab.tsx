"use client";

import { useState } from "react";
import { Camera, Eye } from "../icons";
import { VisualQADialog } from "./visual-qa-dialog";
import type { VisualQAEntityType } from "@/types/rendering";

interface VisualQAPanelTabProps {
  html: string;
  entityType: VisualQAEntityType;
  entityId: number;
}

export function VisualQAPanelTab({ html, entityType, entityId }: VisualQAPanelTabProps) {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <>
      <div className="bg-surface-muted rounded-lg p-3">
        <div className="mb-2 flex items-center gap-2">
          <Camera className="text-foreground-muted h-4 w-4" />
          <h3 className="text-foreground-muted text-xs font-medium uppercase tracking-wider">
            {"Visual QA"}
          </h3>
        </div>

        <p className="text-foreground-muted mb-3 text-xs">
          {"Compare screenshots across email clients"}
        </p>

        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          disabled={!html}
          className="border-border bg-card text-foreground hover:bg-surface-hover inline-flex w-full items-center justify-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
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
