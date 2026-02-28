"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  ApprovalResponse,
  ApprovalDecision,
  FeedbackResponse,
  AuditResponse,
} from "@merkle-email-hub/sdk";

export function useApproval(approvalId: number | null) {
  return useSWR<ApprovalResponse>(
    approvalId ? `/api/v1/approvals/${approvalId}` : null,
    fetcher
  );
}

export function useApprovalDecide(approvalId: number) {
  return useSWRMutation<ApprovalResponse, ApiError, string, ApprovalDecision>(
    `/api/v1/approvals/${approvalId}/decide`,
    mutationFetcher
  );
}

export function useApprovalFeedback(approvalId: number | null) {
  return useSWR<FeedbackResponse[]>(
    approvalId ? `/api/v1/approvals/${approvalId}/feedback` : null,
    fetcher
  );
}

export function useApprovalAudit(approvalId: number | null) {
  return useSWR<AuditResponse[]>(
    approvalId ? `/api/v1/approvals/${approvalId}/audit` : null,
    fetcher
  );
}
