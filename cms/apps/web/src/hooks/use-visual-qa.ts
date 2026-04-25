"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { longMutationFetcher, mutationFetcher } from "@/lib/mutation-fetcher";
import { authFetch } from "@/lib/auth-fetch";
import { ApiError } from "@/lib/api-error";
import type {
  ScreenshotRequest,
  ScreenshotResponse,
  VisualDiffRequest,
  VisualDiffResponse,
  BaselineListResponse,
  BaselineUpdateRequest,
  BaselineResponse,
  VisualQAEntityType,
} from "@/types/rendering";

/** Capture screenshots for current HTML across all client profiles. */
export function useCaptureScreenshots() {
  return useSWRMutation<ScreenshotResponse, ApiError, string, ScreenshotRequest>(
    "/api/v1/rendering/screenshots",
    longMutationFetcher,
  );
}

/** Run visual diff between baseline and current image. */
export function useVisualDiff() {
  return useSWRMutation<VisualDiffResponse, ApiError, string, VisualDiffRequest>(
    "/api/v1/rendering/visual-diff",
    mutationFetcher,
  );
}

/** Fetch baselines for an entity. */
export function useBaselines(entityType: VisualQAEntityType | null, entityId: number | null) {
  const key =
    entityType && entityId ? `/api/v1/rendering/baselines/${entityType}/${entityId}` : null;
  return useSWR<BaselineListResponse, ApiError>(key, fetcher);
}

/** Update (upsert) a baseline image for a specific client. */
export function useUpdateBaseline(entityType: VisualQAEntityType, entityId: number) {
  return useSWRMutation<BaselineResponse, ApiError, string, BaselineUpdateRequest>(
    `/api/v1/rendering/baselines/${entityType}/${entityId}`,
    async (url: string, { arg }: { arg: BaselineUpdateRequest }) => {
      const res = await authFetch(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(arg),
      });

      if (!res.ok) {
        let message = "Failed to update baseline";
        let code: string | undefined;
        try {
          const body = await res.json();
          if (body.error) message = body.error;
          if (body.type) code = body.type;
        } catch {
          message = res.statusText || message;
        }
        throw new ApiError(res.status, message, code);
      }

      return res.json();
    },
  );
}
