"use client";

import { useRef, useCallback } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { CheckCircle2, XCircle, Upload, Loader2 } from "../icons";
import { useBaselines, useUpdateBaseline } from "@/hooks/use-visual-qa";
import type { ClientScreenshot, ClientProfile, VisualQAEntityType } from "@/types/rendering";
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
  const session = useSession();
  const userRole = session.data?.user?.role;
  const canEdit = userRole === "admin" || userRole === "developer";

  const { data: baselinesData, mutate: mutateBaselines } = useBaselines(entityType, entityId);
  const { trigger: updateBaseline, isMutating } = useUpdateBaseline(entityType, entityId);

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
        toast.success("Baseline updated successfully");
      } catch {
        toast.error("Failed to update baseline");
      }
    },
    [updateBaseline, mutateBaselines],
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
      toast.success("Baseline updated successfully");
    } catch {
      toast.error("Failed to update baseline");
    }
  }, [currentScreenshots, updateBaseline, mutateBaselines]);

  return (
    <div className="space-y-4">
      {/* Bulk action */}
      {canEdit && currentScreenshots.length > 0 && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => confirmDialogRef.current?.showModal()}
            disabled={isMutating}
            className="bg-interactive text-on-interactive hover:bg-interactive-hover inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {isMutating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {"Update All Baselines"}
          </button>
        </div>
      )}

      {/* Baselines list */}
      <div className="space-y-3">
        {currentScreenshots.map((screenshot) => {
          const displayName =
            CLIENT_DISPLAY_NAMES[screenshot.client_name as ClientProfile] ?? screenshot.client_name;
          const existing = baselineMap.get(screenshot.client_name);

          return (
            <div
              key={screenshot.client_name}
              className="border-border flex items-center justify-between rounded-lg border p-3"
            >
              <div className="flex items-center gap-3">
                {existing ? (
                  <CheckCircle2 className="text-status-success h-4 w-4" />
                ) : (
                  <XCircle className="text-foreground-muted h-4 w-4" />
                )}
                <div>
                  <p className="text-foreground text-sm font-medium">{displayName}</p>
                  {existing ? (
                    <p className="text-foreground-muted text-xs">
                      {new Date(existing.updated_at).toLocaleDateString()}
                      {" · "}
                      {existing.image_hash.slice(0, 8)}
                    </p>
                  ) : (
                    <p className="text-foreground-muted text-xs">
                      {"No baseline set for this client"}
                    </p>
                  )}
                </div>
              </div>

              {canEdit && (
                <button
                  type="button"
                  onClick={() => handleSetBaseline(screenshot)}
                  disabled={isMutating}
                  className="border-border text-foreground hover:bg-surface-hover rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {existing ? "Update Baseline" : "Set as Baseline"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {currentScreenshots.length === 0 && (
        <p className="text-foreground-muted py-8 text-center text-sm">
          {"Capture screenshots to begin visual QA review"}
        </p>
      )}

      {/* Confirmation dialog for bulk update */}
      <dialog
        ref={confirmDialogRef}
        className="border-border bg-card rounded-lg border p-0 shadow-xl backdrop:bg-black/50"
      >
        <div className="w-96 p-6">
          <h3 className="text-foreground text-base font-semibold">{"Update Baselines"}</h3>
          <p className="text-foreground-muted mt-2 text-sm">
            {
              "This will replace the existing baselines with the current screenshots. This action cannot be undone."
            }
          </p>
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => confirmDialogRef.current?.close()}
              className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm transition-colors"
            >
              {"Cancel"}
            </button>
            <button
              type="button"
              onClick={handleUpdateAll}
              className="bg-interactive text-on-interactive hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
            >
              {"Update"}
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
}
