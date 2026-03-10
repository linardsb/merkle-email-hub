"use client";

import useSWRMutation from "swr/mutation";
import type { ProjectResponse, ProjectUpdate } from "@merkle-email-hub/sdk";
import { authFetch } from "@/lib/auth-fetch";
import { ApiError } from "@/lib/api-error";

export function useUpdateProject(projectId: number) {
  return useSWRMutation<ProjectResponse, Error, string, ProjectUpdate>(
    `/api/v1/projects/${projectId}`,
    async (url: string, { arg }: { arg: ProjectUpdate }) => {
      const res = await authFetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(arg),
      });
      if (!res.ok) {
        let message = "Failed to update project";
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
      return res.json() as Promise<ProjectResponse>;
    }
  );
}
