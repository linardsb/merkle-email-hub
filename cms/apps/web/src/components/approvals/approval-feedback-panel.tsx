"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useSession } from "next-auth/react";
import { MessageSquare, Send, Loader2 } from "lucide-react";
import { useApprovalFeedback, useAddFeedback } from "@/hooks/use-approvals";
import { toast } from "sonner";

interface ApprovalFeedbackPanelProps {
  approvalId: number;
}

export function ApprovalFeedbackPanel({
  approvalId,
}: ApprovalFeedbackPanelProps) {
  const t = useTranslations("approvals");
  const session = useSession();
  const { data: feedback, isLoading, mutate } = useApprovalFeedback(approvalId);
  const { trigger: addFeedback, isMutating } = useAddFeedback(approvalId);
  const [content, setContent] = useState("");

  const canSubmit =
    content.trim().length >= 1 && content.trim().length <= 5000;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit || isMutating) return;
    try {
      await addFeedback({ content: content.trim(), feedback_type: "comment" });
      setContent("");
      await mutate();
      toast.success(t("feedbackSent"));
    } catch {
      toast.error(t("feedbackError"));
    }
  }, [canSubmit, isMutating, addFeedback, content, mutate, t]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Feedback thread */}
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {!feedback?.length ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <MessageSquare className="h-8 w-8 text-foreground-muted" />
            <p className="mt-2 text-sm text-foreground-muted">
              {t("feedbackEmpty")}
            </p>
          </div>
        ) : (
          feedback.map((fb) => (
            <div
              key={fb.id}
              className="rounded-lg border border-card-border bg-card-bg p-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-foreground">
                  User #{fb.author_id}
                </span>
                <span className="text-xs text-foreground-muted">
                  {new Date(fb.created_at as string).toLocaleString()}
                </span>
              </div>
              <p className="mt-1 text-sm text-foreground">{fb.content}</p>
            </div>
          ))
        )}
      </div>

      {/* Add feedback form */}
      {session.data?.user && (
        <div className="border-t border-border p-3">
          <div className="flex gap-2">
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("feedbackPlaceholder")}
              rows={2}
              className="flex-1 resize-none rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted focus:border-input-focus focus:outline-none"
              disabled={isMutating}
            />
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit || isMutating}
              className="self-end rounded-md bg-interactive px-3 py-2 text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
            >
              {isMutating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
          <p className="mt-1 text-xs text-foreground-muted">
            {t("feedbackHint")}
          </p>
        </div>
      )}
    </div>
  );
}
