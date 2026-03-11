import type { BlueprintRunResponse } from "@email-hub/sdk";

export type BlueprintRunStatus = BlueprintRunResponse["status"];

/**
 * A persisted blueprint run record returned by the list/detail API.
 * Wraps the full BlueprintRunResponse with persistence metadata.
 */
export interface BlueprintRunRecord {
  id: number;
  project_id: number;
  blueprint_name: string;
  brief_excerpt: string;
  status: BlueprintRunStatus;
  qa_passed: boolean | null;
  total_tokens: number;
  duration_ms: number;
  created_at: string;
  /** Full run response data (loaded on detail view) */
  run_data: BlueprintRunResponse | null;
}

export type BlueprintRunsFilter = "all" | BlueprintRunStatus;
