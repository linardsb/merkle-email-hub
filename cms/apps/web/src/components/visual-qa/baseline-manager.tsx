"use client";

import { useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import {
  CheckCircle2,
  XCircle,
  Upload,
  Loader2,
} from "lucide-react";
import { useBaselines, useUpdateBaseline } from "@/hooks/use-visual-qa";
import type {
  ClientScreenshot,
  ClientProfile,
  VisualQAEntityType,
} from "@/types/rendering";
import { CLIENT_DISPLAY_NAMES } from "@/types/rendering";

interface BaselineManagerProps {
  entityType: VisualQAEntityType;
  entityId: number;
  currentScreenshots: ClientScreenshot[];
}

export function BaselineManager({
  entityType,
  entityId,
  currentScreenshots,
}: BaselineManagerProps) {
  const t = useTranslations("visualQa");
  const session = useSession();
  const userRole = session.data?.user?.role;
  const canEdit = userRole === "admin" || userRole === "developer";

  const { data: baselinesData, mutate: mutateBaselines } = useBaselines(
    entityType,
    entityId,
  );
  const { trigger: updateBaseline, isMutating } = useUpdateBaseline(
    entityType,
    entityId,
  );

  const confirmDialogRef = useRef<HTMLDialogElement>(null);

  const baselines = baselinesData?.baselines ?? [];
  const baselineMap = new Map(baselines.map((b) => [b.client_name, b]));

  const handleSetBaseline = useCallback(
    async (screenshot: ClientScreenshot) => {
      try {
        await updateBaseline({
          client_name: screenshot.client_name,
          image_base64: screenshot.image_base64,
        });
        await mutateBaselines();
        toast.success(t("baselineUpdated"));
      } catch {
        toast.error(t("baselineUpdateError"));
      }
    },
    [updateBaseline, mutateBaselines, t],
  );

  const handleUpdateAll = useCallback(async () => {
    confirmDialogRef.current?.close();
    try {
      for (const screenshot of currentScreenshots) {
        await updateBaseline({
          client_name: screenshot.client_name,
          image_base64: screenshot.image_base64,
        });
      }
      await mutateBaselines();
      toast.success(t("baselineUpdated"));
    } catch {
      toast.error(t("baselineUpdateError"));
    }
  }, [currentScreenshots, updateBaseline, mutateBaselines, t]);

  return (
    <div className="space-y-4">
      {/* Bulk action */}
      {canEdit && currentScreenshots.length > 0 && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => confirmDialogRef.current?.showModal()}
            disabled={isMutating}
            className="inline-flex items-center gap-2 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-on-interactive transition-colors hover:bg-interactive-hover disabled:opacity-50"
          >
            {isMutating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {t("updateAllBaselines")}
          </button>
        </div>
      )}

      {/* Baselines list */}
      <div className="space-y-3">
        {currentScreenshots.map((screenshot) => {
          const displayName =
            CLIENT_DISPLAY_NAMES[screenshot.client_name as ClientProfile] ??
            screenshot.client_name;
          const existing = baselineMap.get(screenshot.client_name);

          return (
            <div
              key={screenshot.client_name}
              className="flex items-center justify-between rounded-lg border border-border p-3"
            >
              <div className="flex items-center gap-3">
                {existing ? (
                  <CheckCircle2 className="h-4 w-4 text-status-success" />
                ) : (
                  <XCircle className="h-4 w-4 text-foreground-muted" />
                )}
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {displayName}
                  </p>
                  {existing ? (
                    <p className="text-xs text-foreground-muted">
                      {new Date(existing.updated_at).toLocaleDateString()}
                      {" · "}
                      {existing.image_hash.slice(0, 8)}
                    </p>
                  ) : (
                    <p className="text-xs text-foreground-muted">
                      {t("noBaselineSet")}
                    </p>
                  )}
                </div>
              </div>

              {canEdit && (
                <button
                  type="button"
                  onClick={() => handleSetBaseline(screenshot)}
                  disabled={isMutating}
                  className="rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
                >
                  {existing ? t("updateBaseline") : t("setAsBaseline")}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {currentScreenshots.length === 0 && (
        <p className="py-8 text-center text-sm text-foreground-muted">
          {t("captureFirst")}
        </p>
      )}

      {/* Confirmation dialog for bulk update */}
      <dialog
        ref={confirmDialogRef}
        className="rounded-lg border border-border bg-card p-0 shadow-xl backdrop:bg-black/50"
      >
        <div className="w-96 p-6">
          <h3 className="text-base font-semibold text-foreground">
            {t("updateConfirmTitle")}
          </h3>
          <p className="mt-2 text-sm text-foreground-muted">
            {t("updateConfirmDescription")}
          </p>
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => confirmDialogRef.current?.close()}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
            >
              {t("cancel")}
            </button>
            <button
              type="button"
              onClick={handleUpdateAll}
              className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-on-interactive transition-colors hover:bg-interactive-hover"
            >
              {t("updateConfirmAction")}
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
}
