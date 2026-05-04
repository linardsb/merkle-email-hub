"use client";

import { useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { CheckCircle2, XCircle, RotateCcw, Loader2 } from "../icons";
import { useApprovalDecide } from "@/hooks/use-approvals";
import { toast } from "sonner";

interface ApprovalDecisionBarProps {
  approvalId: number;
  currentStatus: string;
  onDecisionMade: () => void;
}

export function ApprovalDecisionBar({
  approvalId,
  currentStatus,
  onDecisionMade,
}: ApprovalDecisionBarProps) {
  const session = useSession();
  const { trigger: decide, isMutating } = useApprovalDecide(approvalId);
  const [reviewNote, setReviewNote] = useState("");

  const userRole = session.data?.user?.role;
  const canDecide = userRole === "admin" || userRole === "developer";
  const isPending = currentStatus === "pending" || currentStatus === "revision_requested";

  const handleDecision = useCallback(
    async (status: "approved" | "rejected" | "revision_requested") => {
      if (isMutating) return;
      try {
        await decide({
          status,
          review_note: reviewNote.trim() || undefined,
        });
        toast.success("Decision submitted");
        onDecisionMade();
      } catch {
        toast.error("Failed to submit decision");
      }
    },
    [isMutating, decide, reviewNote, onDecisionMade],
  );

  if (!canDecide || !isPending) return null;

  return (
    <div className="border-border bg-surface-muted border-t p-4">
      <textarea
        value={reviewNote}
        onChange={(e) => setReviewNote(e.target.value)}
        placeholder={"Add a note about your decision..."}
        rows={2}
        className="border-input-border bg-input-bg text-foreground placeholder:text-foreground-muted focus:border-input-focus w-full resize-none rounded-md border px-3 py-2 text-sm focus:outline-none"
        disabled={isMutating}
      />
      <p className="text-foreground-muted mt-1 mb-3 text-xs">{"Review note (optional)"}</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => handleDecision("approved")}
          disabled={isMutating}
          className="bg-status-success text-foreground-inverse flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors hover:opacity-90 disabled:opacity-50"
        >
          {isMutating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCircle2 className="h-4 w-4" />
          )}
          {"Approve"}
        </button>
        <button
          type="button"
          onClick={() => handleDecision("revision_requested")}
          disabled={isMutating}
          className="border-border bg-surface text-foreground hover:bg-surface-hover flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
        >
          <RotateCcw className="h-4 w-4" />
          {"Request Revision"}
        </button>
        <button
          type="button"
          onClick={() => handleDecision("rejected")}
          disabled={isMutating}
          className="bg-status-danger text-foreground-inverse flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors hover:opacity-90 disabled:opacity-50"
        >
          <XCircle className="h-4 w-4" />
          {"Reject"}
        </button>
      </div>
    </div>
  );
}
