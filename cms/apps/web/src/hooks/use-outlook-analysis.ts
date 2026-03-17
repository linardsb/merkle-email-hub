"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  OutlookAnalysisRequest,
  OutlookAnalysisResponse,
  OutlookModernizeRequest,
  OutlookModernizeResponse,
} from "@/types/outlook";

/** Run Outlook dependency analysis (POST /api/v1/qa/outlook-analysis). */
export function useOutlookAnalysis() {
  return useSWRMutation<OutlookAnalysisResponse, ApiError, string, OutlookAnalysisRequest>(
    "/api/v1/qa/outlook-analysis",
    longMutationFetcher,
  );
}

/** Run Outlook modernization (POST /api/v1/qa/outlook-modernize). */
export function useOutlookModernize() {
  return useSWRMutation<OutlookModernizeResponse, ApiError, string, OutlookModernizeRequest>(
    "/api/v1/qa/outlook-modernize",
    longMutationFetcher,
  );
}
