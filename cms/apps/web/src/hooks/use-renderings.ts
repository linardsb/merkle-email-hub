"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  RenderingClient,
  RenderingTest,
  RenderingComparison,
  RenderingTestRequest,
  PaginatedRenderingTests,
  RenderingDashboardSummary,
} from "@/types/rendering";

export function useRenderingClients() {
  return useSWR<RenderingClient[], ApiError>(
    "/api/v1/renderings/clients",
    fetcher,
  );
}

export function useRenderingTests(params: {
  page?: number;
  pageSize?: number;
  provider?: string | null;
}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.pageSize) searchParams.set("page_size", String(params.pageSize));
  if (params.provider) searchParams.set("provider", params.provider);
  const qs = searchParams.toString();
  return useSWR<PaginatedRenderingTests, ApiError>(
    `/api/v1/renderings/tests${qs ? `?${qs}` : ""}`,
    fetcher,
  );
}

export function useRenderingTest(testId: number | null) {
  return useSWR<RenderingTest, ApiError>(
    testId ? `/api/v1/renderings/tests/${testId}` : null,
    fetcher,
  );
}

export function useRenderingLatest(buildId: number | null) {
  const qs = buildId ? `?build_id=${buildId}` : "";
  return useSWR<RenderingTest, ApiError>(
    `/api/v1/renderings/tests/latest${qs}`,
    fetcher,
  );
}

export function useRequestRendering() {
  return useSWRMutation<RenderingTest, ApiError, string, RenderingTestRequest>(
    "/api/v1/renderings/tests",
    longMutationFetcher,
  );
}

export function useRenderingComparison(testId1: number | null, testId2: number | null) {
  return useSWR<RenderingComparison[], ApiError>(
    testId1 && testId2
      ? `/api/v1/renderings/compare?test_id_1=${testId1}&test_id_2=${testId2}`
      : null,
    fetcher,
  );
}

export function useRenderingSummary() {
  return useSWR<RenderingDashboardSummary, ApiError>(
    "/api/v1/renderings/summary",
    fetcher,
  );
}
