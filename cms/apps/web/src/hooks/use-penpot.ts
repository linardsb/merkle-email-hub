"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";
import type { DesignConnection } from "@/types/design-sync";

const BASE = "/api/v1/design-sync";

/** Filter design-sync connections to penpot provider only */
export function usePenpotConnections() {
  const interval = useSmartPolling(POLL.background);
  const result = useSWR<DesignConnection[]>(`${BASE}/connections`, fetcher, {
    refreshInterval: interval,
    ...SWR_PRESETS.polling,
  });
  return {
    ...result,
    data: result.data?.filter((c) => c.provider === "penpot"),
  };
}
