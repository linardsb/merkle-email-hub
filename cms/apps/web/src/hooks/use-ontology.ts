"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  SyncStatusResponse,
  SyncReportResponse,
  CompetitiveReportResponse,
  EmailClientSchema,
} from "@/types/ontology";

/** GET /api/v1/ontology/sync-status — poll sync state. */
export function useOntologySyncStatus() {
  return useSWR<SyncStatusResponse>(
    "/api/v1/ontology/sync-status",
    fetcher,
    { refreshInterval: 60_000 },
  );
}

/** POST /api/v1/ontology/sync — trigger manual sync (admin only). */
export function useOntologySync() {
  return useSWRMutation<SyncReportResponse, ApiError, string, { dry_run?: boolean }>(
    "/api/v1/ontology/sync",
    longMutationFetcher,
  );
}

/** GET /api/v1/ontology/competitive-report — audience-scoped report. */
export function useCompetitiveReport(clientIds?: string[]) {
  const params = new URLSearchParams();
  if (clientIds?.length) {
    for (const id of clientIds) {
      params.append("client_ids", id);
    }
  }
  const key = clientIds?.length
    ? `/api/v1/ontology/competitive-report?${params.toString()}`
    : "/api/v1/ontology/competitive-report";

  return useSWR<CompetitiveReportResponse>(key, fetcher);
}

/** GET /api/v1/ontology/clients — all email clients from registry. */
export function useEmailClients() {
  return useSWR<EmailClientSchema[]>("/api/v1/ontology/clients", fetcher);
}
