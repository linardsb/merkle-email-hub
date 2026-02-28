"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type { QaRunRequest, QaResultResponse } from "@merkle-email-hub/sdk";

export function useQARun() {
  return useSWRMutation<QaResultResponse, ApiError, string, QaRunRequest>(
    "/api/v1/qa/run",
    longMutationFetcher
  );
}
