/**
 * Collaborative awareness state helpers.
 * Manages cursor positions, selections, and user presence via Yjs Awareness.
 */
import type { Awareness } from "y-protocols/awareness";
import type { ActivityState, Collaborator } from "@/types/collaboration";

/** Cursor palette — 12 distinct colors for peer differentiation */
const CURSOR_COLORS = [
  "#E06C75",
  "#61AFEF",
  "#98C379",
  "#E5C07B",
  "#C678DD",
  "#56B6C2",
  "#BE5046",
  "#D19A66",
  "#7EC8E3",
  "#F4A261",
  "#A78BFA",
  "#34D399",
];

export interface CollabUser {
  name: string;
  color: string;
  role: string;
}

const IDLE_TIMEOUT_MS = 60_000;

/**
 * Set the local user's awareness state.
 * This is shared with all peers in the room.
 */
export function setLocalUser(awareness: Awareness, user: CollabUser): void {
  awareness.setLocalStateField("user", user);
}

/**
 * Get a cursor color for a user based on their client ID.
 */
export function getCursorColor(clientId: number): string {
  return CURSOR_COLORS[clientId % CURSOR_COLORS.length]!;
}

/**
 * Update local activity state + timestamp in awareness.
 */
export function setLocalActivity(awareness: Awareness, activity: ActivityState): void {
  awareness.setLocalStateField("activity", activity);
  awareness.setLocalStateField("lastActiveAt", Date.now());
}

/**
 * Update local cursor/selection in awareness and mark as editing.
 */
export function setLocalCursorState(
  awareness: Awareness,
  cursor: { line: number; col: number } | null,
  selection: { anchor: number; head: number } | null,
): void {
  awareness.setLocalStateField("cursor", cursor);
  awareness.setLocalStateField("selection", selection);
  setLocalActivity(awareness, "editing");
}

/**
 * Derive activity from awareness state based on role and last active time.
 */
export function computeActivity(state: { role?: string; lastActiveAt?: number }): ActivityState {
  if (state.role === "viewer") return "viewing";
  if (!state.lastActiveAt) return "idle";
  return Date.now() - state.lastActiveAt > IDLE_TIMEOUT_MS ? "idle" : "editing";
}

/**
 * Get all remote collaborators from awareness state with enriched activity data.
 */
export function getEnrichedCollaborators(awareness: Awareness): Collaborator[] {
  const states = awareness.getStates();
  const localId = awareness.clientID;
  const collaborators: Collaborator[] = [];

  states.forEach((state, clientId) => {
    if (clientId !== localId && state.user) {
      const user = state.user as CollabUser;
      collaborators.push({
        clientId,
        name: user.name,
        color: user.color || getCursorColor(clientId),
        role: user.role || "developer",
        cursor: (state.cursor as Collaborator["cursor"]) ?? null,
        selection: (state.selection as Collaborator["selection"]) ?? null,
        activity: computeActivity({
          role: user.role,
          lastActiveAt: state.lastActiveAt as number | undefined,
        }),
        lastActiveAt: (state.lastActiveAt as number) ?? 0,
      });
    }
  });

  return collaborators;
}

/**
 * Get all remote collaborators from awareness state (basic version).
 */
export function getCollaborators(awareness: Awareness): Array<CollabUser & { clientId: number }> {
  const states = awareness.getStates();
  const localId = awareness.clientID;
  const collaborators: Array<CollabUser & { clientId: number }> = [];

  states.forEach((state, clientId) => {
    if (clientId !== localId && state.user) {
      collaborators.push({
        clientId,
        name: state.user.name,
        color: state.user.color || getCursorColor(clientId),
        role: state.user.role,
      });
    }
  });

  return collaborators;
}
