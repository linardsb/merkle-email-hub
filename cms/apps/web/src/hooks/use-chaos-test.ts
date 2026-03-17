"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type { ChaosTestRequest, ChaosTestResponse } from "@/types/chaos";

/** Run chaos testing on email HTML (POST /api/v1/qa/chaos-test). */
export function useChaosTest() {
  return useSWRMutation<ChaosTestResponse, ApiError, string, ChaosTestRequest>(
    "/api/v1/qa/chaos-test",
    longMutationFetcher,
  );
}
