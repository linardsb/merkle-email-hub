/**
 * Collaborative awareness state helpers.
 * Manages cursor positions, selections, and user presence via Yjs Awareness.
 */
import type { Awareness } from "y-protocols/awareness";

/** Cursor palette — 12 distinct colors for peer differentiation */
const CURSOR_COLORS = [
  "#E06C75", "#61AFEF", "#98C379", "#E5C07B",
  "#C678DD", "#56B6C2", "#BE5046", "#D19A66",
  "#7EC8E3", "#F4A261", "#A78BFA", "#34D399",
];

export interface CollabUser {
  name: string;
  color: string;
  role: string;
}

/**
 * Set the local user's awareness state.
 * This is shared with all peers in the room.
 */
export function setLocalUser(
  awareness: Awareness,
  user: CollabUser,
): void {
  awareness.setLocalStateField("user", user);
}

/**
 * Get a cursor color for a user based on their client ID.
 */
export function getCursorColor(clientId: number): string {
  return CURSOR_COLORS[clientId % CURSOR_COLORS.length]!;
}

/**
 * Get all remote collaborators from awareness state.
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
