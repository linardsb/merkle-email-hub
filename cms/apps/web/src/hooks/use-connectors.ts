"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type { ExportRequest, ExportResponse } from "@merkle-email-hub/sdk";

export function useExport() {
  return useSWRMutation<ExportResponse, ApiError, string, ExportRequest>(
    "/api/v1/connectors/export",
    longMutationFetcher
  );
}
