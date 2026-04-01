"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";
import type { ApiError } from "@/lib/api-error";

export interface ProgressEntry {
  operation_id: string;
  operation_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  message: string;
  error: string | null;
}

/** Poll operation progress; pauses in background tabs, stops when completed/failed. */
export function useProgress(operationId: string | null) {
  const interval = useSmartPolling(POLL.realtime);
  return useSWR<ProgressEntry, ApiError>(
    operationId ? `/api/v1/progress/${operationId}` : null,
    fetcher,
    {
      refreshInterval: (data: ProgressEntry | undefined) =>
        data && (data.status === "pending" || data.status === "processing") ? interval : POLL.off,
      ...SWR_PRESETS.polling,
    },
  );
}
