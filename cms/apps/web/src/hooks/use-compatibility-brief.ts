"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import { authFetch } from "@/lib/auth-fetch";
import type { CompatibilityBriefResponse } from "@email-hub/sdk";

export function useCompatibilityBrief(projectId: number | null) {
  return useSWR<CompatibilityBriefResponse>(
    projectId ? `/api/v1/projects/${projectId}/compatibility-brief` : null,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 600_000 }
  );
}

export function useRegenerateBrief(projectId: number) {
  const [isRegenerating, setIsRegenerating] = useState(false);

  const regenerate = useCallback(async () => {
    setIsRegenerating(true);
    try {
      await authFetch(`/api/v1/projects/${projectId}/onboarding-brief`, {
        method: "POST",
      });
    } finally {
      setIsRegenerating(false);
    }
  }, [projectId]);

  return { regenerate, isRegenerating };
}
