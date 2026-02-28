"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type {
  PaginatedResponseProjectResponse,
  ProjectResponse,
} from "@merkle-email-hub/sdk";

interface UseProjectsOptions {
  page?: number;
  pageSize?: number;
  clientOrgId?: number;
  search?: string;
}

export function useProjects(options: UseProjectsOptions = {}) {
  const { page = 1, pageSize = 10, clientOrgId, search } = options;

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (clientOrgId) params.set("client_org_id", String(clientOrgId));
  if (search) params.set("search", search);

  const key = `/api/v1/projects?${params.toString()}`;

  return useSWR<PaginatedResponseProjectResponse>(key, fetcher);
}

export function useProject(projectId: number | null) {
  const key = projectId ? `/api/v1/projects/${projectId}` : null;
  return useSWR<ProjectResponse>(key, fetcher);
}
