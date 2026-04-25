"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type { PaginatedResponseComponentResponse } from "@email-hub/sdk";

export function useComponentCoverage() {
  const { data, ...rest } = useSWR<PaginatedResponseComponentResponse>(
    "/api/v1/components/?page=1&page_size=100",
    fetcher,
    { revalidateOnFocus: false },
  );

  const components = data?.items ?? [];
  const coverage = {
    total: components.length,
    full: components.filter((c) => c.compatibility_badge === "full").length,
    partial: components.filter((c) => c.compatibility_badge === "partial").length,
    issues: components.filter((c) => c.compatibility_badge === "issues").length,
    untested: components.filter(
      (c) => !c.compatibility_badge || c.compatibility_badge === "untested",
    ).length,
  };

  return { coverage, isLoading: rest.isLoading, error: rest.error };
}

export function useGraphHealth() {
  return useSWR<{ healthy: boolean }>(
    "graph-health-check",
    async () => {
      try {
        const { authFetch } = await import("@/lib/auth-fetch");
        const res = await authFetch("/api/v1/knowledge/graph/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "health", top_k: 1 }),
        });
        return { healthy: res.ok };
      } catch {
        return { healthy: false };
      }
    },
    { revalidateOnFocus: false, revalidateOnReconnect: false },
  );
}
