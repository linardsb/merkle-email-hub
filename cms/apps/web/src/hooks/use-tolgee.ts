"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher, longMutationFetcher } from "@/lib/mutation-fetcher";
import type { ApiError } from "@/lib/api-error";
import type {
  TolgeeConnectionResponse,
  TolgeeLanguage,
  TranslationSyncResponse,
  TranslationPullResponse,
  LocaleBuildResponse,
} from "@/types/tolgee";

const BASE = "/api/v1/connectors/tolgee";

// ── Connection ───────────────────────────────────────────────────────

export function useTolgeeConnection(connectionId: number | null) {
  return useSWR<TolgeeConnectionResponse>(
    connectionId ? `${BASE}/connections/${connectionId}` : null,
    fetcher,
  );
}

export function useCreateTolgeeConnection() {
  return useSWRMutation<
    TolgeeConnectionResponse,
    ApiError,
    string,
    {
      name: string;
      project_id: number;
      tolgee_project_id: number;
      base_url?: string;
      pat: string;
    }
  >(`${BASE}/connect`, mutationFetcher);
}

// ── Languages ────────────────────────────────────────────────────────

export function useTolgeeLanguages(connectionId: number | null) {
  return useSWR<TolgeeLanguage[]>(
    connectionId ? `${BASE}/connections/${connectionId}/languages` : null,
    fetcher,
  );
}

// ── Key Sync ─────────────────────────────────────────────────────────

export function useSyncKeys() {
  return useSWRMutation<
    TranslationSyncResponse,
    ApiError,
    string,
    { connection_id: number; template_id: number; namespace?: string }
  >(`${BASE}/sync-keys`, mutationFetcher);
}

// ── Pull Translations ────────────────────────────────────────────────

export function usePullTranslations() {
  return useSWRMutation<
    TranslationPullResponse[],
    ApiError,
    string,
    {
      connection_id: number;
      tolgee_project_id: number;
      locales: string[];
      namespace?: string;
    }
  >(`${BASE}/pull`, mutationFetcher);
}

// ── Locale Build ─────────────────────────────────────────────────────

export function useLocaleBuild() {
  return useSWRMutation<
    LocaleBuildResponse,
    ApiError,
    string,
    {
      connection_id: number;
      template_id: number;
      tolgee_project_id: number;
      locales: string[];
      namespace?: string;
      is_production?: boolean;
    }
  >(`${BASE}/build-locales`, longMutationFetcher);
}
