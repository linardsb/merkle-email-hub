"use client";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-badge-warning-bg text-badge-warning-text",
  approved: "bg-badge-success-bg text-badge-success-text",
  rejected: "bg-badge-danger-bg text-badge-danger-text",
  revision_requested: "bg-badge-default-bg text-badge-default-text",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending Review",
  approved: "Approved",
  rejected: "Rejected",
  revision_requested: "Revision Requested",
};

interface ApprovalStatusBadgeProps {
  status: string;
}

export function ApprovalStatusBadge({ status }: ApprovalStatusBadgeProps) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? STATUS_STYLES.pending}`}
    >
      {STATUS_LABELS[status] ?? "Pending Review"}
    </span>
  );
}
