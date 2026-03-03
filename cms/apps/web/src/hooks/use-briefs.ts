"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type {
  BriefConnection,
  BriefItem,
  BriefDetail,
  BriefConnectionCreate,
  BriefImportRequest,
} from "@/types/briefs";

export function useBriefConnections() {
  return useSWR<BriefConnection[]>("/api/v1/briefs/connections", fetcher);
}

export function useBriefItems(connectionId: number | null) {
  return useSWR<BriefItem[]>(
    connectionId ? `/api/v1/briefs/connections/${connectionId}/items` : null,
    fetcher,
  );
}

export function useBriefDetail(itemId: number | null) {
  return useSWR<BriefDetail>(
    itemId ? `/api/v1/briefs/items/${itemId}` : null,
    fetcher,
  );
}

export function useCreateBriefConnection() {
  return useSWRMutation<BriefConnection, Error, string, BriefConnectionCreate>(
    "/api/v1/briefs/connections",
    mutationFetcher,
  );
}

export function useDeleteBriefConnection() {
  return useSWRMutation<{ success: boolean }, Error, string, { id: number }>(
    "/api/v1/briefs/connections/delete",
    mutationFetcher,
  );
}

export function useSyncBriefConnection() {
  return useSWRMutation<BriefConnection, Error, string, { id: number }>(
    "/api/v1/briefs/connections/sync",
    mutationFetcher,
  );
}

export function useImportBrief() {
  return useSWRMutation<{ project_id: number }, Error, string, BriefImportRequest>(
    "/api/v1/briefs/import",
    mutationFetcher,
  );
}
