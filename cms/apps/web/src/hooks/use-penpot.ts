"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type { DesignConnection } from "@/types/design-sync";

const BASE = "/api/v1/design-sync";

/** Filter design-sync connections to penpot provider only */
export function usePenpotConnections() {
  const result = useSWR<DesignConnection[]>(`${BASE}/connections`, fetcher, {
    refreshInterval: 60_000,
  });
  return {
    ...result,
    data: result.data?.filter((c) => c.provider === "penpot"),
  };
}
