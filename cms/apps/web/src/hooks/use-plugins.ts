"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type { PluginListResponse, PluginHealthSummary, PluginInfo } from "@/types/plugins";

const BASE = "/api/v1/plugins";

export function usePlugins() {
  return useSWR<PluginListResponse>(BASE, fetcher, { refreshInterval: 60_000 });
}

export function usePluginHealthSummary() {
  return useSWR<PluginHealthSummary>(`${BASE}/health`, fetcher, { refreshInterval: 60_000 });
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
