"use client";

import useSWRMutation from "swr/mutation";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type { CSSCompileRequest, CSSCompileResponse } from "@/types/css-compiler";

/** Compile CSS for email clients (POST /api/v1/email/compile-css). */
export function useCSSCompile() {
  return useSWRMutation<CSSCompileResponse, ApiError, string, CSSCompileRequest>(
    "/api/v1/email/compile-css",
    longMutationFetcher,
  );
}
