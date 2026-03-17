"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";

interface MCPServerStatus {
  running: boolean;
  transport: string;
  tool_count: number;
  uptime_seconds: number;
}

interface MCPTool {
  name: string;
  description: string;
  category: string;
  enabled: boolean;
}

interface MCPConnection {
  client_id: string;
  connected_at: string;
  last_tool_call: string | null;
  tool_calls_count: number;
}

interface MCPApiKey {
  id: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
}

export function useMCPStatus() {
  return useSWR<MCPServerStatus>("/api/v1/mcp/status", fetcher, {
    refreshInterval: 30_000,
    revalidateOnFocus: false,
  });
}

export function useMCPTools() {
  return useSWR<MCPTool[]>("/api/v1/mcp/tools", fetcher, {
    revalidateOnFocus: false,
  });
}

export function useMCPConnections() {
  return useSWR<MCPConnection[]>("/api/v1/mcp/connections", fetcher, {
    refreshInterval: 15_000,
    revalidateOnFocus: false,
  });
}

export function useToggleMCPTool() {
  return useSWRMutation<void, Error, string, { tool_name: string; enabled: boolean }>(
    "/api/v1/mcp/tools/toggle",
    mutationFetcher,
  );
}

export function useMCPApiKeys() {
  return useSWR<MCPApiKey[]>("/api/v1/mcp/api-keys", fetcher, {
    revalidateOnFocus: false,
  });
}

export function useGenerateMCPApiKey() {
  return useSWRMutation<MCPApiKey, Error, string, { label: string }>(
    "/api/v1/mcp/api-keys",
    mutationFetcher,
  );
}

export type { MCPServerStatus, MCPTool, MCPConnection, MCPApiKey };
