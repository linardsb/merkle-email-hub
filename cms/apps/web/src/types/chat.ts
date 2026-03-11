import type { BlueprintRunResponse } from "@email-hub/sdk";

export type ChatRole = "user" | "assistant";

export type AgentMode =
  | "chat"
  | "scaffolder"
  | "dark_mode"
  | "content"
  | "outlook_fixer"
  | "accessibility"
  | "personalisation"
  | "code_reviewer"
  | "knowledge"
  | "innovation";

export type ChatStatus = "idle" | "streaming" | "error";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: number;
  agent: AgentMode;
  isStreaming: boolean;
  confidence?: number | null;
  blueprintResult?: BlueprintRunResponse | null;
}

/** A single delta inside an SSE chunk choice. */
export interface SSEChunkDelta {
  content?: string;
}

/** A single choice inside an SSE chunk. */
export interface SSEChunkChoice {
  index: number;
  delta: SSEChunkDelta;
  finish_reason: string | null;
}

/** One SSE chunk from the OpenAI-compatible streaming endpoint. */
export interface SSEChunk {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: SSEChunkChoice[];
}

export interface UseChatReturn {
  messages: ChatMessage[];
  status: ChatStatus;
  error: string | null;
  sendMessage: (content: string, agent: AgentMode) => void;
  sendBlueprintRun: (brief: string, options?: { includeHtml?: boolean; currentHtml?: string; projectId?: string }) => void;
  blueprintRunning: boolean;
  stopStreaming: () => void;
  clearMessages: () => void;
  replaceMessages: (messages: ChatMessage[]) => void;
}

/** Maps AgentMode → i18n key in workspace namespace */
export const AGENT_LABEL_KEYS: Record<AgentMode, string> = {
  chat: "chatAgentChat",
  scaffolder: "chatAgentScaffolder",
  dark_mode: "chatAgentDarkMode",
  content: "chatAgentContent",
  outlook_fixer: "chatAgentOutlookFixer",
  accessibility: "chatAgentAccessibility",
  personalisation: "chatAgentPersonalisation",
  code_reviewer: "chatAgentCodeReviewer",
  knowledge: "chatAgentKnowledge",
  innovation: "chatAgentInnovation",
};
