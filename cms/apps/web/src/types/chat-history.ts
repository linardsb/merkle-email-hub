import type { AgentMode, ChatMessage } from "./chat";

export interface ChatSession {
  id: string;
  projectId: string;
  agent: AgentMode;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
  messageCount: number;
  preview: string;
}

export type ChatPanelTab = "chat" | "history";
