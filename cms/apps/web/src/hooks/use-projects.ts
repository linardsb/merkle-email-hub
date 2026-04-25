"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type {
  PaginatedResponseProjectResponse,
  ProjectCreate,
  ProjectResponse,
} from "@email-hub/sdk";

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

export function useCreateProject() {
  return useSWRMutation<ProjectResponse, Error, string, ProjectCreate>(
    "/api/v1/projects",
    mutationFetcher,
  );
}

export function useDeleteProject(id: number | null) {
  return useSWRMutation<void, Error, string, never>(
    id ? `/api/v1/projects/${id}` : "",
    async (url: string) => {
      const { authFetch } = await import("@/lib/auth-fetch");
      const res = await authFetch(url, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete project");
    },
  );
}
