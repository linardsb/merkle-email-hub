import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import { authFetch } from "@/lib/auth-fetch";
import type {
  ESPConnectionResponse,
  ESPConnectionCreate,
  ESPTemplateList,
  ESPTemplate,
  ESPImportRequest,
  ESPPushRequest,
} from "@/types/esp-sync";

const BASE = "/api/v1/connectors/sync";

// --- Connections ---

export function useESPConnections() {
  return useSWR<ESPConnectionResponse[]>(`${BASE}/connections`, fetcher);
}

export function useESPConnection(id: number | null) {
  return useSWR<ESPConnectionResponse>(id ? `${BASE}/connections/${id}` : null, fetcher);
}

export function useCreateESPConnection() {
  return useSWRMutation<ESPConnectionResponse, Error, string, ESPConnectionCreate>(
    `${BASE}/connections`,
    mutationFetcher,
  );
}

export function useDeleteESPConnection(id: number | null) {
  return useSWRMutation<void, Error, string, never>(
    id ? `${BASE}/connections/${id}` : "",
    async (url: string) => {
      const res = await authFetch(url, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete connection");
    },
  );
}

// --- Remote Templates ---

export function useESPTemplates(connectionId: number | null) {
  return useSWR<ESPTemplateList>(
    connectionId ? `${BASE}/connections/${connectionId}/templates` : null,
    fetcher,
  );
}

export function useESPTemplate(connectionId: number | null, templateId: string | null) {
  return useSWR<ESPTemplate>(
    connectionId && templateId
      ? `${BASE}/connections/${connectionId}/templates/${templateId}`
      : null,
    fetcher,
  );
}

// --- Import & Push ---

export function useImportESPTemplate(connectionId: number | null) {
  return useSWRMutation<{ template_id: number }, Error, string, ESPImportRequest>(
    connectionId ? `${BASE}/connections/${connectionId}/import` : "",
    mutationFetcher,
  );
}

export function usePushToESP(connectionId: number | null) {
  return useSWRMutation<ESPTemplate, Error, string, ESPPushRequest>(
    connectionId ? `${BASE}/connections/${connectionId}/push` : "",
    mutationFetcher,
  );
}
