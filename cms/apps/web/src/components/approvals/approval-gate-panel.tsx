"use client";

import { CheckCircle2, ShieldAlert, Clock } from "lucide-react";
import { ApprovalStatusBadge } from "./approval-status-badge";
import type { ApprovalGateResult } from "@/types/approval";

interface ApprovalGatePanelProps {
  approvalResult: ApprovalGateResult;
  onRequestApproval: () => void;
}

export function ApprovalGatePanel({
  approvalResult,
  onRequestApproval,
}: ApprovalGatePanelProps) {
  if (!approvalResult.required) return null;

  if (approvalResult.passed) {
    return (
      <div className="rounded-lg border border-border p-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-status-success" />
          <span className="text-sm font-medium text-status-success">
            {"Approved"}
          </span>
        </div>
        {approvalResult.approved_by && (
          <p className="mt-1 text-xs text-foreground-muted">
            {"Approved by"} {approvalResult.approved_by}
            {approvalResult.approved_at &&
              ` on ${new Date(approvalResult.approved_at).toLocaleDateString()}`}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex items-center gap-2">
        <ShieldAlert className="h-4 w-4 text-status-warning" />
        <span className="text-sm font-medium text-foreground">
          {"Approval Required"}
        </span>
      </div>
      {approvalResult.reason && (
        <p className="mt-1 text-sm text-foreground-muted">
          {approvalResult.reason}
        </p>
      )}
      {approvalResult.approval_id ? (
        <div className="mt-2 flex items-center gap-2">
          <Clock className="h-3.5 w-3.5 text-foreground-muted" />
          <span className="text-xs text-foreground-muted">
            {"Pending review"}
          </span>
          <ApprovalStatusBadge status="pending" />
        </div>
      ) : (
        <button
          type="button"
          onClick={onRequestApproval}
          className="mt-2 text-sm font-medium text-interactive hover:underline"
        >
          {"Submit for Approval"}
        </button>
      )}
    </div>
  );
}
