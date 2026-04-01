"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { POLL, SWR_PRESETS } from "@/lib/swr-constants";
import type { ApiError } from "@/lib/api-error";
import type { PluginListResponse, PluginHealthSummary, PluginInfo } from "@/types/plugins";

const BASE = "/api/v1/plugins";

export function usePlugins() {
  const interval = useSmartPolling(POLL.background);
  return useSWR<PluginListResponse>(BASE, fetcher, {
    refreshInterval: interval,
    ...SWR_PRESETS.polling,
  });
}

export function usePluginHealthSummary() {
  const interval = useSmartPolling(POLL.background);
  return useSWR<PluginHealthSummary>(`${BASE}/health`, fetcher, {
    refreshInterval: interval,
    ...SWR_PRESETS.polling,
  });
}

export function usePluginEnable(name: string) {
  return useSWRMutation<PluginInfo, ApiError, string>(
    `${BASE}/${encodeURIComponent(name)}/enable`,
    mutationFetcher,
  );
}

export function usePluginDisable(name: string) {
  return useSWRMutation<PluginInfo, ApiError, string>(
    `${BASE}/${encodeURIComponent(name)}/disable`,
    mutationFetcher,
  );
}

export function usePluginRestart(name: string) {
  return useSWRMutation<PluginInfo, ApiError, string>(
    `${BASE}/${encodeURIComponent(name)}/restart`,
    mutationFetcher,
  );
}
