"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type { PropertyTestRequest, PropertyTestResponse } from "@/types/chaos";

/** Run property-based tests (POST /api/v1/qa/property-test). */
export function usePropertyTest() {
  return useSWRMutation<PropertyTestResponse, ApiError, string, PropertyTestRequest>(
    "/api/v1/qa/property-test",
    longMutationFetcher,
  );
}
