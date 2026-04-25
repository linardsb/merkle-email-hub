"use client";

import { CheckCircle2, ShieldAlert, Clock } from "../icons";
import { ApprovalStatusBadge } from "./approval-status-badge";
import type { ApprovalGateResult } from "@/types/approval";

interface ApprovalGatePanelProps {
  approvalResult: ApprovalGateResult;
  onRequestApproval: () => void;
}

export function ApprovalGatePanel({ approvalResult, onRequestApproval }: ApprovalGatePanelProps) {
  if (!approvalResult.required) return null;

  if (approvalResult.passed) {
    return (
      <div className="border-border rounded-lg border p-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="text-status-success h-4 w-4" />
          <span className="text-status-success text-sm font-medium">{"Approved"}</span>
        </div>
        {approvalResult.approved_by && (
          <p className="text-foreground-muted mt-1 text-xs">
            {"Approved by"} {approvalResult.approved_by}
            {approvalResult.approved_at &&
              ` on ${new Date(approvalResult.approved_at).toLocaleDateString()}`}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="border-border rounded-lg border p-4">
      <div className="flex items-center gap-2">
        <ShieldAlert className="text-status-warning h-4 w-4" />
        <span className="text-foreground text-sm font-medium">{"Approval Required"}</span>
      </div>
      {approvalResult.reason && (
        <p className="text-foreground-muted mt-1 text-sm">{approvalResult.reason}</p>
      )}
      {approvalResult.approval_id ? (
        <div className="mt-2 flex items-center gap-2">
          <Clock className="text-foreground-muted h-3.5 w-3.5" />
          <span className="text-foreground-muted text-xs">{"Pending review"}</span>
          <ApprovalStatusBadge status="pending" />
        </div>
      ) : (
        <button
          type="button"
          onClick={onRequestApproval}
          className="text-interactive mt-2 text-sm font-medium hover:underline"
        >
          {"Submit for Approval"}
        </button>
      )}
    </div>
  );
}
