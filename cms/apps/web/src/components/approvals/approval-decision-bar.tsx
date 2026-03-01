"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useSession } from "next-auth/react";
import { CheckCircle2, XCircle, RotateCcw, Loader2 } from "lucide-react";
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
  const t = useTranslations("approvals");
  const session = useSession();
  const { trigger: decide, isMutating } = useApprovalDecide(approvalId);
  const [reviewNote, setReviewNote] = useState("");

  const userRole = session.data?.user?.role;
  const canDecide = userRole === "admin" || userRole === "developer";
  const isPending =
    currentStatus === "pending" || currentStatus === "revision_requested";

  const handleDecision = useCallback(
    async (status: "approved" | "rejected" | "revision_requested") => {
      if (isMutating) return;
      try {
        await decide({
          status,
          review_note: reviewNote.trim() || undefined,
        });
        toast.success(t("decisionSuccess"));
        onDecisionMade();
      } catch {
        toast.error(t("decisionError"));
      }
    },
    [isMutating, decide, reviewNote, t, onDecisionMade]
  );

  if (!canDecide || !isPending) return null;

  return (
    <div className="border-t border-border bg-surface-muted p-4">
      <textarea
        value={reviewNote}
        onChange={(e) => setReviewNote(e.target.value)}
        placeholder={t("decisionNotePlaceholder")}
        rows={2}
        className="w-full resize-none rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted focus:border-input-focus focus:outline-none"
        disabled={isMutating}
      />
      <p className="mb-3 mt-1 text-xs text-foreground-muted">
        {t("decisionNoteLabel")}
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => handleDecision("approved")}
          disabled={isMutating}
          className="flex items-center gap-1.5 rounded-md bg-status-success px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:opacity-90 disabled:opacity-50"
        >
          {isMutating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCircle2 className="h-4 w-4" />
          )}
          {t("approve")}
        </button>
        <button
          type="button"
          onClick={() => handleDecision("revision_requested")}
          disabled={isMutating}
          className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          <RotateCcw className="h-4 w-4" />
          {t("requestRevision")}
        </button>
        <button
          type="button"
          onClick={() => handleDecision("rejected")}
          disabled={isMutating}
          className="flex items-center gap-1.5 rounded-md bg-status-danger px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:opacity-90 disabled:opacity-50"
        >
          <XCircle className="h-4 w-4" />
          {t("reject")}
        </button>
      </div>
    </div>
  );
}
