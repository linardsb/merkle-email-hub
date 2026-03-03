export type CollaborationStatus = "connected" | "connecting" | "disconnected";

export interface Collaborator {
  clientId: number;
  name: string;
  color: string;
  cursor?: { line: number; col: number } | null;
}

export interface AwarenessState {
  name: string;
  color: string;
  cursor?: { line: number; col: number } | null;
}
