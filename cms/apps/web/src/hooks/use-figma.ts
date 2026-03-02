"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type {
  FigmaConnection,
  FigmaDesignTokens,
  FigmaConnectionCreate,
} from "@/types/figma";

export function useFigmaConnections() {
  return useSWR<FigmaConnection[]>("/api/v1/figma/connections", fetcher);
}

export function useFigmaConnection(id: number | null) {
  return useSWR<FigmaConnection>(
    id ? `/api/v1/figma/connections/${id}` : null,
    fetcher,
  );
}

export function useFigmaDesignTokens(connectionId: number | null) {
  return useSWR<FigmaDesignTokens>(
    connectionId ? `/api/v1/figma/connections/${connectionId}/tokens` : null,
    fetcher,
  );
}

export function useCreateFigmaConnection() {
  return useSWRMutation<FigmaConnection, Error, string, FigmaConnectionCreate>(
    "/api/v1/figma/connections",
    mutationFetcher,
  );
}

export function useDeleteFigmaConnection() {
  return useSWRMutation<{ success: boolean }, Error, string, { id: number }>(
    "/api/v1/figma/connections/delete",
    mutationFetcher,
  );
}

export function useSyncFigmaConnection() {
  return useSWRMutation<FigmaConnection, Error, string, { id: number }>(
    "/api/v1/figma/connections/sync",
    mutationFetcher,
  );
}
