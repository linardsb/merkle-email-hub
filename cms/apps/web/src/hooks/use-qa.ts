"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { longMutationFetcher, mutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  QARunRequest,
  QAResultResponse,
  QAOverrideRequest,
  QAOverrideResponse,
  PaginatedQAResults,
} from "@/types/qa";

/** Run QA checks (POST /api/v1/qa/run). Long timeout for check execution. */
export function useQARun() {
  return useSWRMutation<QAResultResponse, ApiError, string, QARunRequest>(
    "/api/v1/qa/run",
    longMutationFetcher
  );
}

/** Get a specific QA result by ID. */
export function useQAResult(resultId: number | null) {
  return useSWR<QAResultResponse>(
    resultId ? `/api/v1/qa/results/${resultId}` : null,
    fetcher
  );
}

/** Get the latest QA result for a template version. */
export function useQALatest(templateVersionId: number | null) {
  return useSWR<QAResultResponse>(
    templateVersionId
      ? `/api/v1/qa/results/latest?template_version_id=${templateVersionId}`
      : null,
    fetcher
  );
}

/** List QA results with pagination and filters. */
export function useQAResults(
  options: {
    page?: number;
    pageSize?: number;
    templateVersionId?: number | null;
    passed?: boolean | null;
  } = {}
) {
  const { page = 1, pageSize = 20, templateVersionId, passed } = options;
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (templateVersionId)
    params.set("template_version_id", String(templateVersionId));
  if (passed !== null && passed !== undefined)
    params.set("passed", String(passed));

  return useSWR<PaginatedQAResults>(
    `/api/v1/qa/results?${params.toString()}`,
    fetcher
  );
}

/** Override failing QA checks (POST /api/v1/qa/results/{id}/override). Developer+ only. */
export function useQAOverride(resultId: number | null) {
  return useSWRMutation<
    QAOverrideResponse,
    ApiError,
    string | null,
    QAOverrideRequest
  >(
    resultId ? `/api/v1/qa/results/${resultId}/override` : null,
    mutationFetcher
  );
}
