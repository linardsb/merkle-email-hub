"use client";

import { FileText } from "../icons";
import { ApprovalStatusBadge } from "./approval-status-badge";
import type { ApprovalResponse } from "@email-hub/sdk";

interface ApprovalCardProps {
  approval: ApprovalResponse;
  onClick: (approval: ApprovalResponse) => void;
}

export function ApprovalCard({ approval, onClick }: ApprovalCardProps) {
  return (
    <button
      type="button"
      onClick={() => onClick(approval)}
      className="border-card-border bg-card-bg hover:border-interactive w-full rounded-lg border p-4 text-left transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-surface-muted flex h-10 w-10 items-center justify-center rounded-md">
            <FileText className="text-foreground-muted h-5 w-5" />
          </div>
          <div>
            <p className="text-foreground text-sm font-medium">Build #{approval.build_id}</p>
            <p className="text-foreground-muted text-xs">
              {`Requested by User #${approval.requested_by_id}`}
            </p>
          </div>
        </div>
        <ApprovalStatusBadge status={approval.status} />
      </div>
      <p className="text-foreground-muted mt-3 text-xs">
        {"Submitted"}: {new Date(approval.created_at as string).toLocaleDateString()}
      </p>
    </button>
  );
}
