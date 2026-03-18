"use client";

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
  label: "Submitted for review",
} as const;

const ACTION_CONFIG: Record<
  string,
  { icon: LucideIcon; colorClass: string; label: string }
> = {
  submitted: {
    icon: Send,
    colorClass: "text-interactive",
    label: "Submitted for review",
  },
  approved: {
    icon: CheckCircle2,
    colorClass: "text-status-success",
    label: "Approved",
  },
  rejected: {
    icon: XCircle,
    colorClass: "text-status-danger",
    label: "Rejected",
  },
  revision_requested: {
    icon: RotateCcw,
    colorClass: "text-status-warning",
    label: "Revision requested",
  },
  feedback_added: {
    icon: MessageSquare,
    colorClass: "text-foreground-muted",
    label: "Feedback added",
  },
};

interface ApprovalAuditTimelineProps {
  approvalId: number;
}

export function ApprovalAuditTimeline({
  approvalId,
}: ApprovalAuditTimelineProps) {
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
        {"No audit entries yet"}
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
                {config.label}
              </p>
              <p className="text-xs text-foreground-muted">
                {`Requested by User #\${entry.actor_id}`} &middot;{" "}
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
