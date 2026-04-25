"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type { FailurePatternListResponse, FailurePatternStats } from "@/types/failure-patterns";

export function useFailurePatterns(options: {
  page?: number;
  pageSize?: number;
  projectId?: number;
  agentName?: string;
  qaCheck?: string;
  clientId?: string;
}) {
  const params = new URLSearchParams();
  params.set("page", String(options.page ?? 1));
  params.set("page_size", String(options.pageSize ?? 20));
  if (options.projectId) params.set("project_id", String(options.projectId));
  if (options.agentName) params.set("agent_name", options.agentName);
  if (options.qaCheck) params.set("qa_check", options.qaCheck);
  if (options.clientId) params.set("client_id", options.clientId);

  return useSWR<FailurePatternListResponse>(
    `/api/v1/blueprints/failure-patterns?${params.toString()}`,
    fetcher,
  );
}

export function useFailurePatternStats(projectId?: number) {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", String(projectId));

  return useSWR<FailurePatternStats>(
    `/api/v1/blueprints/failure-patterns/stats?${params.toString()}`,
    fetcher,
  );
}
