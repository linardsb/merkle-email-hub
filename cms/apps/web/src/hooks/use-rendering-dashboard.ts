"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type { ScreenshotResponse, ScreenshotRequest } from "@/types/rendering";
import type {
  CalibrationSummaryResponse,
  CalibrationHistoryResponse,
} from "@/types/rendering-dashboard";

const RENDERING_BASE = "/api/v1/rendering";

/** Trigger screenshot capture with confidence scores. */
export function useScreenshotsWithConfidence() {
  return useSWRMutation<ScreenshotResponse, ApiError, string, ScreenshotRequest>(
    `${RENDERING_BASE}/screenshots`,
    longMutationFetcher,
  );
}

/** Read calibration summary for all emulators. */
export function useCalibrationSummary() {
  return useSWR<CalibrationSummaryResponse, ApiError>(
    `${RENDERING_BASE}/calibration/summary`,
    fetcher,
  );
}

/** Read calibration history for a specific client. Pass null to skip. */
export function useCalibrationHistory(clientId: string | null) {
  return useSWR<CalibrationHistoryResponse, ApiError>(
    clientId ? `${RENDERING_BASE}/calibration/history/${clientId}` : null,
    fetcher,
  );
}

/** Trigger recalibration (admin only). */
export function useTriggerCalibration() {
  return useSWRMutation<{ triggered: boolean }, ApiError, string, { client_id?: string }>(
    `${RENDERING_BASE}/calibration/trigger`,
    longMutationFetcher,
  );
}
