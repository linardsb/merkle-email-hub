"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type { PaginatedResponseClientOrgResponse } from "@merkle-email-hub/sdk";

interface UseOrgsOptions {
  page?: number;
  pageSize?: number;
}

export function useOrgs(options: UseOrgsOptions = {}) {
  const { page = 1, pageSize = 50 } = options;

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  const key = `/api/v1/orgs?${params.toString()}`;

  return useSWR<PaginatedResponseClientOrgResponse>(key, fetcher);
}
