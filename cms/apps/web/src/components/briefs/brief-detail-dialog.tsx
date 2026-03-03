"use client";

import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@merkle-email-hub/ui/components/ui/dialog";
import { Calendar, Users, Paperclip, Tag, AlertCircle, Loader2 } from "lucide-react";
import { useBriefDetail } from "@/hooks/use-briefs";

interface BriefDetailDialogProps {
  itemId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function BriefDetailDialog({ itemId, open, onOpenChange }: BriefDetailDialogProps) {
  const t = useTranslations("briefs");
  const { data: detail, isLoading } = useBriefDetail(open ? itemId : null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[28rem]">
        <DialogHeader>
          <DialogTitle className="text-base">
            {detail?.external_id ? `${detail.external_id} — ` : ""}
            {detail?.title ?? t("detailTitle")}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
          </div>
        ) : detail ? (
          <div className="space-y-4">
            {/* Meta */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-foreground-muted">
              {detail.priority && (
                <span className="flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {t("priorityLabel", { priority: detail.priority })}
                </span>
              )}
              {detail.assignees.length > 0 && (
                <span className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {detail.assignees.join(", ")}
                </span>
              )}
              {detail.due_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {new Date(detail.due_date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </span>
              )}
            </div>

            {/* Labels */}
            {detail.labels.length > 0 && (
              <div className="flex flex-wrap gap-1">
                <Tag className="mt-0.5 h-3 w-3 text-foreground-muted" />
                {detail.labels.map((label) => (
                  <span
                    key={label}
                    className="rounded bg-surface-muted px-1.5 py-0.5 text-xs text-foreground-muted"
                  >
                    {label}
                  </span>
                ))}
              </div>
            )}

            {/* Description */}
            <div className="prose-sm max-h-60 overflow-y-auto rounded border border-card-border bg-surface-muted p-3 text-sm text-foreground whitespace-pre-wrap">
              {detail.description || t("noDescription")}
            </div>

            {/* Attachments */}
            {detail.attachments.length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-medium text-foreground">{t("attachments")}</p>
                <div className="space-y-1">
                  {detail.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center gap-2 rounded border border-card-border px-2 py-1.5 text-xs text-foreground-muted"
                    >
                      <Paperclip className="h-3 w-3 shrink-0" />
                      <span className="truncate">{att.filename}</span>
                      <span className="ml-auto shrink-0">
                        {(att.size_bytes / 1024).toFixed(0)} KB
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-foreground-muted">{t("detailNotFound")}</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
