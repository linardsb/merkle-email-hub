"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import { authFetch } from "@/lib/auth-fetch";
import { ApiError } from "@/lib/api-error";
import type {
  PaginatedTemplates,
  TemplateResponse,
  TemplateCreate,
  VersionResponse,
  VersionCreate,
} from "@/types/templates";

// ── Read Hooks ──

interface UseTemplatesOptions {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
}

export function useTemplates(projectId: number | null, options: UseTemplatesOptions = {}) {
  const { page = 1, pageSize = 50, search, status } = options;

  let key: string | null = null;
  if (projectId) {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    key = `/api/v1/projects/${projectId}/templates?${params.toString()}`;
  }

  return useSWR<PaginatedTemplates>(key, fetcher);
}

export function useTemplate(templateId: number | null) {
  const key = templateId ? `/api/v1/templates/${templateId}` : null;
  return useSWR<TemplateResponse>(key, fetcher);
}

export function useTemplateVersions(templateId: number | null) {
  const key = templateId ? `/api/v1/templates/${templateId}/versions` : null;
  return useSWR<VersionResponse[]>(key, fetcher);
}

export function useTemplateVersion(templateId: number | null, versionNumber: number | null) {
  const key =
    templateId && versionNumber
      ? `/api/v1/templates/${templateId}/versions/${versionNumber}`
      : null;
  return useSWR<VersionResponse>(key, fetcher);
}

// ── Mutation Hooks ──

export function useCreateTemplate(projectId: number | null) {
  const key = projectId ? `/api/v1/projects/${projectId}/templates` : null;
  return useSWRMutation<TemplateResponse, ApiError, string | null, TemplateCreate>(
    key,
    mutationFetcher,
  );
}

export function useSaveVersion(templateId: number | null) {
  const key = templateId ? `/api/v1/templates/${templateId}/versions` : null;
  return useSWRMutation<VersionResponse, ApiError, string | null, VersionCreate>(
    key,
    mutationFetcher,
  );
}

async function patchFetcher<T>(url: string, { arg }: { arg: unknown }): Promise<T> {
  const res = await authFetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(arg),
  });
  if (!res.ok) {
    let message = "Request failed";
    let code: string | undefined;
    try {
      const body = await res.json();
      if (body.error) message = body.error;
      if (body.type) code = body.type;
    } catch {
      message = res.statusText || message;
    }
    throw new ApiError(res.status, message, code);
  }
  return res.json();
}

export function useUpdateTemplate(templateId: number | null) {
  const key = templateId ? `/api/v1/templates/${templateId}` : null;
  return useSWRMutation(key, patchFetcher);
}

async function restoreFetcher<T>(
  url: string,
  { arg }: { arg: { version_number: number } },
): Promise<T> {
  const res = await authFetch(`${url}/restore/${arg.version_number}`, {
    method: "POST",
  });
  if (!res.ok) {
    let message = "Request failed";
    let code: string | undefined;
    try {
      const body = await res.json();
      if (body.error) message = body.error;
      if (body.type) code = body.type;
    } catch {
      message = res.statusText || message;
    }
    throw new ApiError(res.status, message, code);
  }
  return res.json();
}

export function useRestoreVersion(templateId: number | null) {
  const key = templateId ? `/api/v1/templates/${templateId}` : null;
  return useSWRMutation<VersionResponse, ApiError, string | null, { version_number: number }>(
    key,
    restoreFetcher,
  );
}
