"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  BuildRequest,
  BuildResponse,
  PreviewRequest,
  PreviewResponse,
} from "@email-hub/sdk";

export function useEmailBuild() {
  return useSWRMutation<BuildResponse, ApiError, string, BuildRequest>(
    "/api/v1/email/build",
    longMutationFetcher
  );
}

export function useEmailPreview() {
  return useSWRMutation<PreviewResponse, ApiError, string, PreviewRequest>(
    "/api/v1/email/preview",
    longMutationFetcher
  );
}
