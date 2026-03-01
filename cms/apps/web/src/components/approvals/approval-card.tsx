"use client";

import { useTranslations } from "next-intl";
import { FileText } from "lucide-react";
import { ApprovalStatusBadge } from "./approval-status-badge";
import type { ApprovalResponse } from "@merkle-email-hub/sdk";

interface ApprovalCardProps {
  approval: ApprovalResponse;
  onClick: (approval: ApprovalResponse) => void;
}

export function ApprovalCard({ approval, onClick }: ApprovalCardProps) {
  const t = useTranslations("approvals");

  return (
    <button
      type="button"
      onClick={() => onClick(approval)}
      className="w-full rounded-lg border border-card-border bg-card-bg p-4 text-left transition-colors hover:border-interactive"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-surface-muted">
            <FileText className="h-5 w-5 text-foreground-muted" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              Build #{approval.build_id}
            </p>
            <p className="text-xs text-foreground-muted">
              {t("requestedBy", { userId: approval.requested_by_id })}
            </p>
          </div>
        </div>
        <ApprovalStatusBadge status={approval.status} />
      </div>
      <p className="mt-3 text-xs text-foreground-muted">
        {t("createdAt")}:{" "}
        {new Date(approval.created_at as string).toLocaleDateString()}
      </p>
    </button>
  );
}
