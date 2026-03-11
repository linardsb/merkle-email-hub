"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type { AgentSkillsResponse } from "@/types/agent-skills";

export function useAgentSkills() {
  return useSWR<AgentSkillsResponse>(
    "/api/v1/agents/skills",
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 600_000 }
  );
}
