"use client";

import { useTranslations } from "next-intl";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-badge-warning-bg text-badge-warning-text",
  approved: "bg-badge-success-bg text-badge-success-text",
  rejected: "bg-badge-danger-bg text-badge-danger-text",
  revision_requested: "bg-badge-default-bg text-badge-default-text",
};

const STATUS_KEYS: Record<string, string> = {
  pending: "statusPending",
  approved: "statusApproved",
  rejected: "statusRejected",
  revision_requested: "statusRevisionRequested",
};

interface ApprovalStatusBadgeProps {
  status: string;
}

export function ApprovalStatusBadge({ status }: ApprovalStatusBadgeProps) {
  const t = useTranslations("approvals");

  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? STATUS_STYLES.pending}`}
    >
      {t(STATUS_KEYS[status] ?? "statusPending")}
    </span>
  );
}
