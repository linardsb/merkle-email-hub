/**
 * Demo collaboration provider.
 * Simulates a second user with cursor movements for demo mode.
 * Uses an in-memory Yjs doc (no WebSocket needed).
 */
import * as Y from "yjs";
import type { Awareness } from "y-protocols/awareness";

const DEMO_USER = {
  name: "Sarah Chen",
  color: "#8b5cf6",
};

const DEMO_COLORS = ["#8b5cf6", "#ec4899", "#f59e0b", "#10b981"];

/**
 * Starts a simulated second user for demo mode.
 * Returns a cleanup function.
 */
export function startDemoCollaborator(
  awareness: Awareness,
): () => void {
  // Simulate a second client by setting a remote state
  const fakeClientId = 999;

  // Simulate cursor movements
  let cursorLine = 5;
  let direction = 1;

  const interval = setInterval(() => {
    cursorLine += direction;
    if (cursorLine > 20) direction = -1;
    if (cursorLine < 3) direction = 1;

    // We can't directly set another client's awareness state via the public API,
    // but we can expose the demo user info through our own awareness
    // The hook will merge this simulated user into the collaborator list
    const currentState = awareness.getLocalState() ?? {};
    awareness.setLocalState({
      ...currentState,
      demoCollaborators: [
        {
          clientId: fakeClientId,
          name: DEMO_USER.name,
          color: DEMO_USER.color,
          role: "developer",
          cursor: { line: cursorLine, col: Math.floor(Math.random() * 40) + 1 },
          selection: null,
          activity: "editing" as const,
          lastActiveAt: Date.now(),
        },
      ],
    });
  }, 3000);

  return () => {
    clearInterval(interval);
  };
}

export function getDemoUserColors(): string[] {
  return DEMO_COLORS;
}
