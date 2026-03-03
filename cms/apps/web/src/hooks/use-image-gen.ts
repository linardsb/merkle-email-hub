"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { GeneratedImage, ImageGenRequest, ImageGenResponse } from "@/types/image-gen";

export function useProjectImages(projectId: number | null) {
  return useSWR<GeneratedImage[]>(
    projectId ? `/api/v1/projects/${projectId}/images` : null,
    fetcher,
  );
}

export function useGenerateImage() {
  return useSWRMutation<ImageGenResponse, Error, string, ImageGenRequest>(
    "/api/v1/images/generate",
    mutationFetcher,
  );
}
