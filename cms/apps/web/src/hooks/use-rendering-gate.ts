"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import { authFetch } from "@/lib/auth-fetch";
import { ApiError } from "@/lib/api-error";
import type {
  GateResult,
  GateEvaluateRequest,
  RenderingGateConfig,
  GateConfigUpdateRequest,
} from "@/types/rendering-gate";

const BASE = "/api/v1/rendering/gate";

/** Trigger gate evaluation (POST — mutation, not cached read). */
export function useGateEvaluate() {
  return useSWRMutation<GateResult, ApiError, string, GateEvaluateRequest>(
    `${BASE}/evaluate`,
    longMutationFetcher,
  );
}

/** Read project gate config. Pass null to skip. */
export function useGateConfig(projectId: number | null) {
  return useSWR<RenderingGateConfig, ApiError>(
    projectId ? `${BASE}/config/${projectId}` : null,
    fetcher,
  );
}

async function putMutationFetcher<T>(
  url: string,
  { arg }: { arg: unknown },
): Promise<T> {
  const res = await authFetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(arg),
  });
  if (!res.ok) {
    let message = "Request failed";
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
}

/** Update project gate config (admin only). */
export function useUpdateGateConfig(projectId: number | null) {
  return useSWRMutation<RenderingGateConfig, ApiError, string, GateConfigUpdateRequest>(
    projectId ? `${BASE}/config/${projectId}` : "",
    putMutationFetcher,
  );
}
