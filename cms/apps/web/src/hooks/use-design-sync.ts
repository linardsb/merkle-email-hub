"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher, longMutationFetcher } from "@/lib/mutation-fetcher";
import { authFetch } from "@/lib/auth-fetch";
import { ApiError } from "@/lib/api-error";
import type {
  DesignConnection,
  DesignTokens,
  DesignConnectionCreate,
  DesignFileStructure,
  DesignComponentList,
  ImageExportResult,
  ExportImagesArg,
  GeneratedBrief,
  GenerateBriefArg,
  DesignImport,
  CreateImportArg,
  ConvertImportArg,
  ExtractComponentsResult,
  ExtractComponentsArg,
  BrowseFilesResponse,
  BrowseFilesArg,
} from "@/types/design-sync";

// ── Browse files (wizard) ──

export function useBrowseDesignFiles() {
  return useSWRMutation<BrowseFilesResponse, Error, string, BrowseFilesArg>(
    "/api/v1/design-sync/browse-files",
    mutationFetcher,
  );
}

// ── Existing hooks ──

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

// ── 12.8: Design reference panel hooks ──

export function useDesignImportByTemplate(templateId: number | null, projectId: number) {
  return useSWR<DesignImport | null>(
    templateId
      ? `/api/v1/design-sync/imports/by-template/${templateId}?project_id=${projectId}`
      : null,
    fetcher,
  );
}

// ── 12.7: File browser & import hooks ──

export function useDesignFileStructure(connectionId: number | null, depth?: number) {
  const depthParam = depth ? `?depth=${depth}` : "";
  return useSWR<DesignFileStructure>(
    connectionId ? `/api/v1/design-sync/connections/${connectionId}/file-structure${depthParam}` : null,
    fetcher,
  );
}

export function useDesignComponents(connectionId: number | null) {
  return useSWR<DesignComponentList>(
    connectionId ? `/api/v1/design-sync/connections/${connectionId}/components` : null,
    fetcher,
  );
}

export function useExportImages() {
  return useSWRMutation<ImageExportResult, Error, string, ExportImagesArg>(
    "/api/v1/design-sync/connections/export-images",
    mutationFetcher,
  );
}

export function useGenerateBrief() {
  return useSWRMutation<GeneratedBrief, Error, string, GenerateBriefArg>(
    "/api/v1/design-sync/connections/generate-brief",
    mutationFetcher,
  );
}

export function useCreateDesignImport() {
  return useSWRMutation<DesignImport, Error, string, CreateImportArg>(
    "/api/v1/design-sync/imports",
    mutationFetcher,
  );
}

export function useDesignImport(importId: number | null, polling?: boolean) {
  return useSWR<DesignImport>(
    importId ? `/api/v1/design-sync/imports/${importId}` : null,
    fetcher,
    { refreshInterval: polling ? 2000 : 0 },
  );
}

export function useUpdateImportBrief(importId: number | null) {
  return useSWRMutation<DesignImport, Error, string, { generated_brief: string }>(
    importId ? `/api/v1/design-sync/imports/${importId}/brief` : "",
    async (url: string, { arg }: { arg: { generated_brief: string } }) => {
      const res = await authFetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(arg),
      });
      if (!res.ok) {
        let message = "Failed to update brief";
        try {
          const body = await res.json();
          if (body.error) message = body.error;
        } catch { /* use default */ }
        throw new ApiError(res.status, message);
      }
      return res.json();
    },
  );
}

export function useConvertImport(importId: number | null) {
  return useSWRMutation<DesignImport, Error, string, ConvertImportArg>(
    importId ? `/api/v1/design-sync/imports/${importId}/convert` : "",
    longMutationFetcher,
  );
}

export function useExtractComponents(connectionId: number | null) {
  return useSWRMutation<ExtractComponentsResult, Error, string, ExtractComponentsArg>(
    connectionId ? `/api/v1/design-sync/connections/${connectionId}/extract-components` : "",
    mutationFetcher,
  );
}
