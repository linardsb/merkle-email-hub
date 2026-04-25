"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  ApprovalResponse,
  ApprovalCreate,
  ApprovalDecision,
  FeedbackResponse,
  AuditResponse,
  BuildResponse,
} from "@email-hub/sdk";

/** List approvals for a project. */
export function useApprovals(projectId: number | null) {
  return useSWR<ApprovalResponse[]>(
    projectId ? `/api/v1/approvals/?project_id=${projectId}` : null,
    fetcher,
  );
}

/** Get a single approval by ID. */
export function useApproval(approvalId: number | null) {
  return useSWR<ApprovalResponse>(approvalId ? `/api/v1/approvals/${approvalId}` : null, fetcher);
}

/** Submit a template for approval. */
export function useCreateApproval() {
  return useSWRMutation<ApprovalResponse, ApiError, string, ApprovalCreate>(
    "/api/v1/approvals/",
    mutationFetcher,
  );
}

/** Approve, reject, or request revision. */
export function useApprovalDecide(approvalId: number) {
  return useSWRMutation<ApprovalResponse, ApiError, string, ApprovalDecision>(
    `/api/v1/approvals/${approvalId}/decide`,
    mutationFetcher,
  );
}

/** List feedback on an approval. */
export function useApprovalFeedback(approvalId: number | null) {
  return useSWR<FeedbackResponse[]>(
    approvalId ? `/api/v1/approvals/${approvalId}/feedback` : null,
    fetcher,
  );
}

/** Add feedback to an approval. */
export function useAddFeedback(approvalId: number) {
  return useSWRMutation<
    FeedbackResponse,
    ApiError,
    string,
    { content: string; feedback_type?: string }
  >(`/api/v1/approvals/${approvalId}/feedback`, mutationFetcher);
}

/** Get audit trail for an approval. */
export function useApprovalAudit(approvalId: number | null) {
  return useSWR<AuditResponse[]>(
    approvalId ? `/api/v1/approvals/${approvalId}/audit` : null,
    fetcher,
  );
}

/** Get an email build (for preview HTML). */
export function useBuild(buildId: number | null) {
  return useSWR<BuildResponse>(buildId ? `/api/v1/email/builds/${buildId}` : null, fetcher);
}
