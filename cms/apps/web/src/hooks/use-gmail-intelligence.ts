"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  GmailPredictRequest,
  GmailPredictResponse,
  GmailOptimizeRequest,
  GmailOptimizeResponse,
  DeliverabilityScoreRequest,
  DeliverabilityScoreResponse,
  BIMICheckRequest,
  BIMICheckResponse,
} from "@/types/gmail-intelligence";

/** Predict Gmail AI summary (POST /api/v1/qa/gmail-predict). */
export function useGmailPredict() {
  return useSWRMutation<GmailPredictResponse, ApiError, string, GmailPredictRequest>(
    "/api/v1/qa/gmail-predict",
    longMutationFetcher,
  );
}

/** Optimize email for Gmail AI summary (POST /api/v1/qa/gmail-optimize). */
export function useGmailOptimize() {
  return useSWRMutation<GmailOptimizeResponse, ApiError, string, GmailOptimizeRequest>(
    "/api/v1/qa/gmail-optimize",
    longMutationFetcher,
  );
}

/** Score email deliverability (POST /api/v1/qa/deliverability-score). */
export function useDeliverabilityScore() {
  return useSWRMutation<DeliverabilityScoreResponse, ApiError, string, DeliverabilityScoreRequest>(
    "/api/v1/qa/deliverability-score",
    longMutationFetcher,
  );
}

/** Check BIMI readiness for a domain (POST /api/v1/qa/bimi-check). */
export function useBIMICheck() {
  return useSWRMutation<BIMICheckResponse, ApiError, string, BIMICheckRequest>(
    "/api/v1/qa/bimi-check",
    longMutationFetcher,
  );
}
