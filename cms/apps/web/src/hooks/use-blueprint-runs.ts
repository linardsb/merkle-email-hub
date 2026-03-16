"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type { BlueprintRunRecord } from "@/types/blueprint-runs";
import type { CheckpointListResponse } from "@email-hub/sdk";

interface BlueprintRunsResponse {
  items: BlueprintRunRecord[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Fetch paginated blueprint run history for a project.
 */
export function useBlueprintRuns(projectId: number | null, status?: string) {
  const params = new URLSearchParams();
  if (status && status !== "all") params.set("status", status);
  params.set("page_size", "50");

  const key = projectId
    ? `/api/v1/projects/${projectId}/blueprint-runs?${params.toString()}`
    : null;

  return useSWR<BlueprintRunsResponse>(key, fetcher, {
    revalidateOnFocus: false,
  });
}

/**
 * Fetch a single blueprint run detail by ID.
 */
export function useBlueprintRunDetail(runId: number | null) {
  const key = runId ? `/api/v1/blueprint-runs/${runId}` : null;
  return useSWR<BlueprintRunRecord>(key, fetcher, {
    revalidateOnFocus: false,
  });
}

/**
 * Fetch checkpoints for a specific blueprint run.
 * Pass null runId to skip fetching (lazy load on expand).
 */
export function useRunCheckpoints(runId: string | null) {
  const key = runId ? `/api/v1/blueprints/runs/${runId}/checkpoints` : null;
  return useSWR<CheckpointListResponse>(key, fetcher, {
    revalidateOnFocus: false,
  });
}
