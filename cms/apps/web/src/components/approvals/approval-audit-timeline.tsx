"use client";

import { useTranslations } from "next-intl";
import {
  Send,
  CheckCircle2,
  XCircle,
  RotateCcw,
  MessageSquare,
  Loader2,
} from "lucide-react";
import { useApprovalAudit } from "@/hooks/use-approvals";
import type { LucideIcon } from "lucide-react";

const DEFAULT_ACTION = {
  icon: Send,
  colorClass: "text-interactive",
  labelKey: "auditSubmitted",
} as const;

const ACTION_CONFIG: Record<
  string,
  { icon: LucideIcon; colorClass: string; labelKey: string }
> = {
  submitted: {
    icon: Send,
    colorClass: "text-interactive",
    labelKey: "auditSubmitted",
  },
  approved: {
    icon: CheckCircle2,
    colorClass: "text-status-success",
    labelKey: "auditApproved",
  },
  rejected: {
    icon: XCircle,
    colorClass: "text-status-danger",
    labelKey: "auditRejected",
  },
  revision_requested: {
    icon: RotateCcw,
    colorClass: "text-status-warning",
    labelKey: "auditRevisionRequested",
  },
  feedback_added: {
    icon: MessageSquare,
    colorClass: "text-foreground-muted",
    labelKey: "auditFeedbackAdded",
  },
};

interface ApprovalAuditTimelineProps {
  approvalId: number;
}

export function ApprovalAuditTimeline({
  approvalId,
}: ApprovalAuditTimelineProps) {
  const t = useTranslations("approvals");
  const { data: entries, isLoading } = useApprovalAudit(approvalId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
      </div>
    );
  }

  if (!entries?.length) {
    return (
      <p className="py-8 text-center text-sm text-foreground-muted">
        {t("auditEmpty")}
      </p>
    );
  }

  return (
    <div className="space-y-0 p-4">
      {entries.map((entry, idx) => {
        const config = ACTION_CONFIG[entry.action] ?? DEFAULT_ACTION;
        const Icon = config.icon;
        const isLast = idx === entries.length - 1;

        return (
          <div key={entry.id} className="flex gap-3">
            {/* Timeline line + icon */}
            <div className="flex flex-col items-center">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full bg-surface-muted ${config.colorClass}`}
              >
                <Icon className="h-4 w-4" />
              </div>
              {!isLast && <div className="w-px flex-1 bg-border" />}
            </div>

            {/* Content */}
            <div className={isLast ? "pb-0" : "pb-6"}>
              <p className="text-sm font-medium text-foreground">
                {t(config.labelKey)}
              </p>
              <p className="text-xs text-foreground-muted">
                {t("requestedBy", { userId: entry.actor_id })} &middot;{" "}
                {new Date(entry.created_at as string).toLocaleString()}
              </p>
              {entry.details && (
                <p className="mt-1 text-sm text-foreground-muted">
                  {entry.details}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
