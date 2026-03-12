"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type {
  DesignConnection,
  DesignTokens,
  DesignConnectionCreate,
} from "@/types/design-sync";

export function useDesignConnections() {
  return useSWR<DesignConnection[]>("/api/v1/design-sync/connections", fetcher);
}

export function useDesignConnection(id: number | null) {
  return useSWR<DesignConnection>(
    id ? `/api/v1/design-sync/connections/${id}` : null,
    fetcher,
  );
}

export function useDesignTokens(connectionId: number | null) {
  return useSWR<DesignTokens>(
    connectionId ? `/api/v1/design-sync/connections/${connectionId}/tokens` : null,
    fetcher,
  );
}

export function useCreateDesignConnection() {
  return useSWRMutation<DesignConnection, Error, string, DesignConnectionCreate>(
    "/api/v1/design-sync/connections",
    mutationFetcher,
  );
}

export function useDeleteDesignConnection() {
  return useSWRMutation<{ success: boolean }, Error, string, { id: number }>(
    "/api/v1/design-sync/connections/delete",
    mutationFetcher,
  );
}

export function useSyncDesignConnection() {
  return useSWRMutation<DesignConnection, Error, string, { id: number }>(
    "/api/v1/design-sync/connections/sync",
    mutationFetcher,
  );
}
