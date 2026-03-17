"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  SchemaInjectRequest,
  SchemaInjectResponse,
} from "@/types/gmail-intelligence";

/** Inject schema.org markup into email HTML (POST /api/v1/email/inject-schema). */
export function useSchemaInject() {
  return useSWRMutation<SchemaInjectResponse, ApiError, string, SchemaInjectRequest>(
    "/api/v1/email/inject-schema",
    longMutationFetcher,
  );
}
