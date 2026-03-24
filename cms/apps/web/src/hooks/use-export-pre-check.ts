"use client";

import useSWRMutation from "swr/mutation";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  ExportPreCheckRequest,
  ExportPreCheckResponse,
} from "@/types/approval";

const BASE = "/api/v1/connectors/export";

/** Trigger combined QA + rendering + approval pre-check before export. */
export function useExportPreCheck() {
  return useSWRMutation<
    ExportPreCheckResponse,
    ApiError,
    string,
    ExportPreCheckRequest
  >(`${BASE}/pre-check`, mutationFetcher);
}
