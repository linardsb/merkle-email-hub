"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import { authFetch } from "@/lib/auth-fetch";
import type {
  PaginatedResponseComponentResponse,
  ComponentResponse,
  AppComponentsSchemasVersionResponse as VersionResponse,
  ComponentCompatibilityResponse,
} from "@email-hub/sdk";

interface UseComponentsOptions {
  page?: number;
  pageSize?: number;
  category?: string;
  search?: string;
}

export function useComponents(options: UseComponentsOptions = {}) {
  const { page = 1, pageSize = 20, category, search } = options;

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (category) params.set("category", category);
  if (search) params.set("search", search);

  return useSWR<PaginatedResponseComponentResponse>(
    `/api/v1/components/?${params.toString()}`,
    fetcher
  );
}

export function useComponent(componentId: number | null) {
  return useSWR<ComponentResponse>(
    componentId ? `/api/v1/components/${componentId}` : null,
    fetcher
  );
}

export function useComponentVersions(componentId: number | null) {
  return useSWR<VersionResponse[]>(
    componentId ? `/api/v1/components/${componentId}/versions` : null,
    fetcher
  );
}

export function useComponentCompatibility(componentId: number | null) {
  return useSWR<ComponentCompatibilityResponse>(
    componentId ? `/api/v1/components/${componentId}/compatibility` : null,
    fetcher
  );
}

// ── Mutations ──

interface ComponentCreate {
  name: string;
  slug: string;
  description?: string;
  category?: string;
  html_source: string;
  css_source?: string;
}

interface ComponentUpdate {
  name?: string;
  description?: string;
  category?: string;
}

interface VersionCreate {
  html_source: string;
  css_source?: string;
  changelog?: string;
  slot_definitions?: unknown[];
  default_tokens?: Record<string, unknown>;
}

export function useCreateComponent() {
  return useSWRMutation<ComponentResponse, Error, string, ComponentCreate>(
    "/api/v1/components/",
    mutationFetcher
  );
}

export function useUpdateComponent(id: number | null) {
  return useSWRMutation<ComponentResponse, Error, string, ComponentUpdate>(
    id ? `/api/v1/components/${id}` : "",
    async (url: string, { arg }: { arg: ComponentUpdate }) => {
      const res = await authFetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(arg),
      });
      if (!res.ok) throw new Error("Failed to update component");
      return res.json();
    }
  );
}

export function useDeleteComponent(id: number | null) {
  return useSWRMutation<void, Error, string, never>(
    id ? `/api/v1/components/${id}` : "",
    async (url: string) => {
      const res = await authFetch(url, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete component");
    }
  );
}

export function useCreateVersion(componentId: number | null) {
  return useSWRMutation<VersionResponse, Error, string, VersionCreate>(
    componentId ? `/api/v1/components/${componentId}/versions` : "",
    mutationFetcher
  );
}

/**
 * Trigger QA checks for a specific component version.
 */
export function useRunComponentQA(
  componentId: number | null,
  versionNumber: number | null,
) {
  return useSWRMutation<unknown, Error, string, Record<string, never>>(
    componentId && versionNumber
      ? `/api/v1/components/${componentId}/versions/${versionNumber}/qa`
      : "",
    mutationFetcher,
  );
}
