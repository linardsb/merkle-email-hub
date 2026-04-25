"use client";

import { useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { MessageSquare, Send, Loader2 } from "../icons";
import { useApprovalFeedback, useAddFeedback } from "@/hooks/use-approvals";
import { toast } from "sonner";

interface ApprovalFeedbackPanelProps {
  approvalId: number;
}

export function ApprovalFeedbackPanel({ approvalId }: ApprovalFeedbackPanelProps) {
  const session = useSession();
  const { data: feedback, isLoading, mutate } = useApprovalFeedback(approvalId);
  const { trigger: addFeedback, isMutating } = useAddFeedback(approvalId);
  const [content, setContent] = useState("");

  const canSubmit = content.trim().length >= 1 && content.trim().length <= 5000;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit || isMutating) return;
    try {
      await addFeedback({ content: content.trim(), feedback_type: "comment" });
      setContent("");
      await mutate();
      toast.success("Feedback submitted");
    } catch {
      toast.error("Failed to submit feedback");
    }
  }, [canSubmit, isMutating, addFeedback, content, mutate]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="text-foreground-muted h-5 w-5 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Feedback thread */}
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {!feedback?.length ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <MessageSquare className="text-foreground-muted h-8 w-8" />
            <p className="text-foreground-muted mt-2 text-sm">{"No feedback yet"}</p>
          </div>
        ) : (
          feedback.map((fb) => (
            <div key={fb.id} className="border-card-border bg-card-bg rounded-lg border p-3">
              <div className="flex items-center justify-between">
                <span className="text-foreground text-xs font-medium">
                  {`Requested by User #${fb.author_id}`}
                </span>
                <span className="text-foreground-muted text-xs">
                  {new Date(fb.created_at as string).toLocaleString()}
                </span>
              </div>
              <p className="text-foreground mt-1 text-sm">{fb.content}</p>
            </div>
          ))
        )}
      </div>

      {/* Add feedback form */}
      {session.data?.user && (
        <div className="border-border border-t p-3">
          <div className="flex gap-2">
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={"Leave feedback on this template..."}
              rows={2}
              className="border-input-border bg-input-bg text-foreground placeholder:text-foreground-muted focus:border-input-focus flex-1 resize-none rounded-md border px-3 py-2 text-sm focus:outline-none"
              disabled={isMutating}
            />
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit || isMutating}
              className="bg-interactive text-foreground-inverse hover:bg-interactive-hover self-end rounded-md px-3 py-2 transition-colors disabled:opacity-50"
            >
              {isMutating ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Send className="h-4 w-4" aria-hidden />
              )}
              <span className="sr-only">{"Sending..."}</span>
            </button>
          </div>
          <p className="text-foreground-muted mt-1 text-xs">{"1-5000 characters"}</p>
        </div>
      )}
    </div>
  );
}
