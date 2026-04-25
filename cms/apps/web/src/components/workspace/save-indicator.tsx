"use client";

import { Check, Loader2 } from "../icons";

export type SaveStatus = "idle" | "unsaved" | "saving" | "saved" | "error";

interface SaveIndicatorProps {
  status: SaveStatus;
}

export function SaveIndicator({ status }: SaveIndicatorProps) {
  if (status === "idle") return null;

  return (
    <span className="flex items-center gap-1.5 text-xs">
      {status === "unsaved" && (
        <>
          <span className="bg-destructive h-1.5 w-1.5 rounded-full" />
          <span className="text-muted-foreground">{"Unsaved changes"}</span>
        </>
      )}
      {status === "saving" && (
        <>
          <Loader2 className="text-muted-foreground h-3 w-3 animate-spin" />
          <span className="text-muted-foreground">{"Saving..."}</span>
        </>
      )}
      {status === "saved" && (
        <>
          <Check className="text-primary h-3 w-3" />
          <span className="text-muted-foreground">{"Saved"}</span>
        </>
      )}
      {status === "error" && <span className="text-destructive">{"Failed to save"}</span>}
    </span>
  );
}
