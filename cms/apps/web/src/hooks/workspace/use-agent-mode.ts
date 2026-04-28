"use client";

import { useSearchParams } from "next/navigation";
import type { AgentMode } from "@/types/chat";

const VALID_AGENTS: AgentMode[] = [
  "chat",
  "scaffolder",
  "dark_mode",
  "content",
  "outlook_fixer",
  "accessibility",
  "personalisation",
  "code_reviewer",
  "knowledge",
  "innovation",
];

/**
 * Read the initial agent from the `?agent=` query param. Used when the user
 * lands on the workspace from a project-creation flow that pre-selects an
 * agent. Returns `undefined` for missing or invalid values.
 */
export function useAgentMode(): AgentMode | undefined {
  const searchParams = useSearchParams();
  const agentParam = searchParams.get("agent");
  if (!agentParam) return undefined;
  return VALID_AGENTS.includes(agentParam as AgentMode) ? (agentParam as AgentMode) : undefined;
}
