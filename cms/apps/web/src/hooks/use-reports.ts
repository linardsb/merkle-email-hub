"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  ReportResponse,
  ReportDownload,
  QAReportRequest,
  ApprovalPackageRequest,
  RegressionReportRequest,
} from "@/types/reports";

const BASE = "/api/v1/reports";

export function useGenerateQAReport() {
  return useSWRMutation<ReportResponse, ApiError, string, QAReportRequest>(
    `${BASE}/qa`,
    longMutationFetcher,
  );
}

export function useGenerateApprovalReport() {
  return useSWRMutation<ReportResponse, ApiError, string, ApprovalPackageRequest>(
    `${BASE}/approval`,
    longMutationFetcher,
  );
}

export function useGenerateRegressionReport() {
  return useSWRMutation<ReportResponse, ApiError, string, RegressionReportRequest>(
    `${BASE}/regression`,
    longMutationFetcher,
  );
}

export function useReportDownload(reportId: string | null) {
  return useSWRMutation<ReportDownload, ApiError, string>(
    reportId ? `${BASE}/${reportId}` : "",
    async (url: string) => {
      const { authFetch } = await import("@/lib/auth-fetch");
      const res = await authFetch(url);
      if (!res.ok) throw new Error("Failed to download report");
      return res.json();
    },
  );
}
