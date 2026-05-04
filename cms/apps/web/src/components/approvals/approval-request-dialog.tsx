"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2, ShieldCheck } from "../icons";
import { toast } from "sonner";
import { useCreateApproval } from "@/hooks/use-approvals";
import { useExportPreCheck } from "@/hooks/use-export-pre-check";
import { mutationFetcher } from "@/lib/mutation-fetcher";

interface ApprovalRequestDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  buildId: number | null;
  projectId: number;
  compiledHtml: string | null;
  onSubmitted: () => void;
}

export function ApprovalRequestDialog({
  open,
  onOpenChange,
  buildId,
  projectId,
  compiledHtml,
  onSubmitted,
}: ApprovalRequestDialogProps) {
  const [note, setNote] = useState("");
  const { trigger: createApproval, isMutating } = useCreateApproval();
  const { trigger: triggerPreCheck, data: preCheckData } = useExportPreCheck();

  // Reset & trigger pre-check when dialog opens
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setNote("");
    if (compiledHtml) {
      triggerPreCheck({ html: compiledHtml, project_id: projectId }).catch(() => {
        /* pre-check is informational */
      });
    }
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const handleSubmit = async () => {
    if (!buildId) {
      toast.error("No build available — compile the template first");
      return;
    }
    try {
      const approval = await createApproval({ build_id: buildId, project_id: projectId });

      // Post reviewer note as feedback if provided
      if (note.trim() && approval?.id) {
        await mutationFetcher(`/api/v1/approvals/${approval.id}/feedback`, {
          arg: { content: note.trim(), feedback_type: "note" },
        }).catch(() => {
          /* feedback is best-effort */
        });
      }

      toast.success("Build submitted for approval");
      onSubmitted();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit for approval";
      toast.error(message);
    }
  };

  const qaResult = preCheckData?.qa;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[32rem]">
        <DialogHeader>
          <DialogTitle>{"Submit for Approval"}</DialogTitle>
          <DialogDescription>{"Submit this build for review before export"}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Build info */}
          <div className="border-border bg-surface-subtle rounded-md border p-3">
            <div className="flex items-center gap-2 text-sm">
              <ShieldCheck className="text-foreground-muted h-4 w-4" />
              <span className="text-foreground-muted">{"Build"}</span>
              <span className="text-foreground font-medium">
                {buildId ? `#${buildId}` : "Not available"}
              </span>
            </div>
          </div>

          {/* QA summary from pre-check */}
          {qaResult && (
            <div className="flex items-center gap-2 text-sm">
              <span
                className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                  qaResult.passed
                    ? "bg-badge-success-bg text-badge-success-text"
                    : "bg-badge-warning-bg text-badge-warning-text"
                }`}
              >
                {"QA"}
              </span>
              <span className="text-foreground-muted">
                {qaResult.passed
                  ? "All checks passed"
                  : `${qaResult.blocking_failures.length} blocking, ${qaResult.warnings.length} warnings`}
              </span>
            </div>
          )}

          {/* Optional note */}
          <div>
            <label
              htmlFor="approval-note"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Note for reviewer"}
            </label>
            <textarea
              id="approval-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add context for the reviewer..."
              rows={3}
              maxLength={2000}
              className="border-input-border bg-input-bg text-foreground placeholder:text-foreground-muted focus:border-interactive focus:ring-interactive w-full rounded-md border px-3 py-2 text-sm focus:ring-1 focus:outline-none"
            />
          </div>
        </div>

        {/* Actions */}
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
            onClick={handleSubmit}
            disabled={!buildId || isMutating}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Submitting…"}
              </span>
            ) : (
              "Submit for Approval"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
