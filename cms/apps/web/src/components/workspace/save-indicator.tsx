"use client";

import { useTranslations } from "next-intl";
import { Check, Loader2 } from "lucide-react";

export type SaveStatus = "idle" | "unsaved" | "saving" | "saved" | "error";

interface SaveIndicatorProps {
  status: SaveStatus;
}

export function SaveIndicator({ status }: SaveIndicatorProps) {
  const t = useTranslations("workspace");

  if (status === "idle") return null;

  return (
    <span className="flex items-center gap-1.5 text-xs">
      {status === "unsaved" && (
        <>
          <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
          <span className="text-muted-foreground">{t("unsavedChanges")}</span>
        </>
      )}
      {status === "saving" && (
        <>
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          <span className="text-muted-foreground">{t("saving")}</span>
        </>
      )}
      {status === "saved" && (
        <>
          <Check className="h-3 w-3 text-primary" />
          <span className="text-muted-foreground">{t("saved")}</span>
        </>
      )}
      {status === "error" && (
        <span className="text-destructive">{t("saveError")}</span>
      )}
    </span>
  );
}
