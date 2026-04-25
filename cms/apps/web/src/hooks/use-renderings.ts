"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";
import type { ApiError } from "@/lib/api-error";
import type {
  RenderingTest,
  RenderingTestRequest,
  RenderingComparisonRequest,
  RenderingComparisonResponse,
  PaginatedRenderingTests,
} from "@/types/rendering";

export function useRenderingTests(params: {
  page?: number;
  pageSize?: number;
  status?: string | null;
}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.pageSize) searchParams.set("page_size", String(params.pageSize));
  if (params.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return useSWR<PaginatedRenderingTests, ApiError>(
    `/api/v1/rendering/tests${qs ? `?${qs}` : ""}`,
    fetcher,
  );
}

export function useRenderingTest(testId: number | null) {
  return useSWR<RenderingTest, ApiError>(
    testId ? `/api/v1/rendering/tests/${testId}` : null,
    fetcher,
  );
}

/** Poll every 3s while test is pending or processing; pauses in background tabs. */
export function useRenderingTestPolling(testId: number | null) {
  const interval = useSmartPolling(POLL.realtime);
  return useSWR<RenderingTest, ApiError>(
    testId ? `/api/v1/rendering/tests/${testId}` : null,
    fetcher,
    {
      refreshInterval: (data: RenderingTest | undefined) =>
        data && (data.status === "pending" || data.status === "processing") ? interval : POLL.off,
      ...SWR_PRESETS.polling,
    },
  );
}

export function useRequestRendering() {
  return useSWRMutation<RenderingTest, ApiError, string, RenderingTestRequest>(
    "/api/v1/rendering/tests",
    longMutationFetcher,
  );
}

/** POST-based comparison — use as mutation, not SWR read. */
export function useRenderingComparison() {
  return useSWRMutation<RenderingComparisonResponse, ApiError, string, RenderingComparisonRequest>(
    "/api/v1/rendering/compare",
    longMutationFetcher,
  );
}
