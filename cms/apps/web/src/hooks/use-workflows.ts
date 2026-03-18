"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type { WorkflowListResponse, WorkflowStatus, ExecutionLogsResponse } from "@/types/workflows";

const BASE = "/api/v1/workflows";

export function useWorkflows() {
  return useSWR<WorkflowListResponse>(BASE, fetcher, { refreshInterval: 60_000 });
}

/** Poll a specific execution — pass null executionId to skip */
export function useWorkflowStatus(executionId: string | null, isActive = false) {
  return useSWR<WorkflowStatus>(
    executionId ? `${BASE}/${executionId}` : null,
    fetcher,
    { refreshInterval: isActive ? 5_000 : 30_000 },
  );
}

export function useWorkflowLogs(executionId: string | null) {
  return useSWR<ExecutionLogsResponse>(
    executionId ? `${BASE}/${executionId}/logs` : null,
    fetcher,
  );
}

export interface TriggerWorkflowInput {
  flow_id: string;
  inputs?: Record<string, unknown>;
  project_id?: number;
}

export function useTriggerWorkflow() {
  return useSWRMutation<WorkflowStatus, ApiError, string, TriggerWorkflowInput>(
    `${BASE}/trigger`,
    mutationFetcher,
  );
}
