"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type {
  PaginatedResponseComponentResponse,
  ComponentResponse,
  VersionResponse,
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
