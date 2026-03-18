export type CollaborationStatus = "connected" | "connecting" | "disconnected";

export type ActivityState = "editing" | "idle" | "viewing";

export interface Collaborator {
  clientId: number;
  name: string;
  color: string;
  role: string;
  cursor?: { line: number; col: number } | null;
  selection?: { anchor: number; head: number } | null;
  activity: ActivityState;
  lastActiveAt: number;
}

export interface AwarenessState {
  name: string;
  color: string;
  role: string;
  cursor?: { line: number; col: number } | null;
  selection?: { anchor: number; head: number } | null;
  activity: ActivityState;
  lastActiveAt: number;
}

export interface FollowTarget {
  clientId: number;
  name: string;
}
