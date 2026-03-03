"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { BrandConfig } from "@/types/brand";

export function useBrandConfig(orgId: number | null) {
  return useSWR<BrandConfig>(
    orgId ? `/api/v1/orgs/${orgId}/brand` : null,
    fetcher,
  );
}

export function useUpdateBrandConfig() {
  return useSWRMutation<BrandConfig, Error, string, Partial<BrandConfig>>(
    "/api/v1/orgs/brand",
    mutationFetcher,
  );
}
