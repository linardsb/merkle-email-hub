export type ChatRole = "user" | "assistant";

export type AgentMode = "chat" | "scaffolder" | "dark_mode" | "content";

export type ChatStatus = "idle" | "streaming" | "error";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: number;
  agent: AgentMode;
  isStreaming: boolean;
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
  stopStreaming: () => void;
  clearMessages: () => void;
}
