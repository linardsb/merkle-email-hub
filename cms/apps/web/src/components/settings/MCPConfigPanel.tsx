"use client";

import { useState } from "react";
import { Server, Shield, Key, Activity, Copy, Check } from "../icons";
import { toast } from "sonner";
import {
  useMCPStatus,
  useMCPTools,
  useMCPConnections,
  useToggleMCPTool,
  useMCPApiKeys,
  useGenerateMCPApiKey,
} from "@/hooks/use-mcp";

export function MCPConfigPanel() {
  const { data: status } = useMCPStatus();
  const { data: tools, mutate: refreshTools } = useMCPTools();
  const { data: connections } = useMCPConnections();
  const { data: apiKeys, mutate: refreshKeys } = useMCPApiKeys();
  const { trigger: toggleTool } = useToggleMCPTool();
  const { trigger: generateKey, isMutating: generatingKey } = useGenerateMCPApiKey();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleToggleTool = async (toolName: string, enabled: boolean) => {
    try {
      await toggleTool({ tool_name: toolName, enabled });
      await refreshTools();
    } catch {
      toast.error("MCP server not available");
    }
  };

  const handleGenerateKey = async () => {
    try {
      const result = await generateKey({ label: `key-${Date.now()}` });
      if (result) {
        toast.success("API key generated");
        await refreshKeys();
      }
    } catch {
      toast.error("MCP server not available");
    }
  };

  const copyToClipboard = (text: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedKey(text);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const toolsByCategory = (tools ?? []).reduce<Record<string, typeof tools>>((acc, tool) => {
    const cat = tool.category || "other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat]!.push(tool);
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-6">
      {/* Server Status */}
      <div className="border-default bg-card rounded-lg border p-4">
        <div className="flex items-center gap-3">
          <Server className="text-muted-foreground h-5 w-5" />
          <div>
            <h4 className="text-foreground text-sm font-medium">{"Server Status"}</h4>
            <div className="mt-1 flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${status?.running ? "bg-status-success" : "bg-status-danger"}`}
              />
              <span className="text-muted-foreground text-xs">
                {status?.running ? "Running" : "Stopped"}
              </span>
              {status?.running && (
                <span className="text-muted-foreground text-xs">
                  · {status.tool_count} {"tools available"}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tool Allowlist */}
      <div className="border-default bg-card rounded-lg border p-4">
        <div className="mb-3 flex items-center gap-2">
          <Shield className="text-muted-foreground h-4 w-4" />
          <h4 className="text-foreground text-sm font-medium">{"Tool Allowlist"}</h4>
        </div>
        <div className="flex flex-col gap-4">
          {Object.entries(toolsByCategory).map(([category, categoryTools]) => (
            <div key={category}>
              <p className="text-muted-foreground mb-2 text-xs font-medium tracking-wide uppercase">
                {category}
              </p>
              <div className="flex flex-col gap-1">
                {(categoryTools ?? []).map((tool) => (
                  <label
                    key={tool.name}
                    className="hover:bg-accent flex cursor-pointer items-center gap-2 rounded px-2 py-1.5"
                  >
                    <input
                      type="checkbox"
                      checked={tool.enabled}
                      onChange={(e) => handleToggleTool(tool.name, e.target.checked)}
                      className="border-border text-interactive focus:ring-interactive rounded"
                    />
                    <span className="text-foreground text-sm">{tool.name}</span>
                    <span className="text-muted-foreground truncate text-xs">
                      {tool.description}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Connection Log */}
      <div className="border-default bg-card rounded-lg border p-4">
        <div className="mb-3 flex items-center gap-2">
          <Activity className="text-muted-foreground h-4 w-4" />
          <h4 className="text-foreground text-sm font-medium">{"Connection Log"}</h4>
        </div>
        {connections && connections.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-default text-muted-foreground border-b text-left">
                  <th className="pr-4 pb-2">{"Client ID"}</th>
                  <th className="pr-4 pb-2">{"Connected"}</th>
                  <th className="pr-4 pb-2">{"Tool Calls"}</th>
                  <th className="pb-2">{"Last Call"}</th>
                </tr>
              </thead>
              <tbody>
                {connections.map((conn) => (
                  <tr key={conn.client_id} className="border-default/50 border-b">
                    <td className="text-foreground py-2 pr-4 font-mono">
                      {conn.client_id.slice(0, 12)}
                    </td>
                    <td className="text-muted-foreground py-2 pr-4">
                      {new Date(conn.connected_at).toLocaleString()}
                    </td>
                    <td className="text-foreground py-2 pr-4">{conn.tool_calls_count}</td>
                    <td className="text-muted-foreground py-2">
                      {conn.last_tool_call
                        ? new Date(conn.last_tool_call).toLocaleString()
                        : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted-foreground text-xs">{"No recent connections"}</p>
        )}
      </div>

      {/* API Keys */}
      <div className="border-default bg-card rounded-lg border p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key className="text-muted-foreground h-4 w-4" />
            <h4 className="text-foreground text-sm font-medium">{"API Keys"}</h4>
          </div>
          <button
            type="button"
            onClick={handleGenerateKey}
            disabled={generatingKey}
            className="bg-interactive text-foreground-inverse hover:bg-interactive/90 rounded px-3 py-1.5 text-xs font-medium disabled:opacity-50"
          >
            {"Generate Key"}
          </button>
        </div>
        {apiKeys && apiKeys.length > 0 ? (
          <div className="flex flex-col gap-2">
            {apiKeys.map((key) => (
              <div
                key={key.id}
                className="border-default/50 flex items-center justify-between rounded border px-3 py-2"
              >
                <span className="text-foreground font-mono text-xs">{key.key_prefix}...</span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(key.key_prefix)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  {copiedKey === key.key_prefix ? (
                    <Check className="text-status-success h-3.5 w-3.5" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-xs">{"No API keys created"}</p>
        )}
      </div>
    </div>
  );
}
