import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { Awareness } from "y-protocols/awareness";

// Mock awareness module
vi.mock("@/lib/collaboration/awareness", () => ({
  getEnrichedCollaborators: vi.fn(() => []),
  setLocalActivity: vi.fn(),
  setLocalCursorState: vi.fn(),
}));

import { usePresence } from "@/hooks/use-presence";
import {
  getEnrichedCollaborators,
  setLocalActivity,
  setLocalCursorState,
} from "@/lib/collaboration/awareness";
import type { Collaborator } from "@/types/collaboration";

function makeAwarenessMock() {
  const handlers = new Map<string, Set<(...args: unknown[]) => void>>();
  return {
    on(event: string, handler: (...args: unknown[]) => void) {
      if (!handlers.has(event)) handlers.set(event, new Set());
      handlers.get(event)!.add(handler);
    },
    off(event: string, handler: (...args: unknown[]) => void) {
      handlers.get(event)?.delete(handler);
    },
    emit(event: string, ...args: unknown[]) {
      handlers.get(event)?.forEach((h) => h(...args));
    },
    _handlers: handlers,
  };
}

function makeCollaborator(overrides: Partial<Collaborator> = {}): Collaborator {
  return {
    clientId: 1,
    name: "Alice",
    color: "#E06C75",
    role: "admin",
    cursor: null,
    selection: null,
    activity: "editing",
    lastActiveAt: Date.now(),
    ...overrides,
  };
}

describe("usePresence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getEnrichedCollaborators).mockReturnValue([]);
  });

  it("returns empty collaborators initially", () => {
    const { result } = renderHook(() =>
      usePresence({ awareness: null, role: "admin" }),
    );
    expect(result.current.collaborators).toEqual([]);
    expect(result.current.followTarget).toBeNull();
  });

  it("collaborators list updates from awareness state", () => {
    const awareness = makeAwarenessMock();
    const alice = makeCollaborator({ clientId: 1, name: "Alice" });
    vi.mocked(getEnrichedCollaborators).mockReturnValue([alice]);

    const { result } = renderHook(() =>
      usePresence({ awareness: awareness as unknown as Awareness, role: "admin" }),
    );

    expect(result.current.collaborators).toEqual([alice]);
  });

  it("awareness change event updates collaborators", () => {
    const awareness = makeAwarenessMock();
    vi.mocked(getEnrichedCollaborators).mockReturnValue([]);

    const { result } = renderHook(() =>
      usePresence({ awareness: awareness as unknown as Awareness, role: "admin" }),
    );

    expect(result.current.collaborators).toEqual([]);

    const bob = makeCollaborator({ clientId: 2, name: "Bob" });
    vi.mocked(getEnrichedCollaborators).mockReturnValue([bob]);

    act(() => awareness.emit("change"));
    expect(result.current.collaborators).toEqual([bob]);
  });

  it("startFollowing sets followTarget", () => {
    const awareness = makeAwarenessMock();
    const carol = makeCollaborator({ clientId: 5, name: "Carol" });
    vi.mocked(getEnrichedCollaborators).mockReturnValue([carol]);

    const { result } = renderHook(() =>
      usePresence({ awareness: awareness as unknown as Awareness, role: "admin" }),
    );

    act(() => result.current.startFollowing(5, "Carol"));
    expect(result.current.followTarget).toEqual({
      clientId: 5,
      name: "Carol",
    });
  });

  it("stopFollowing clears followTarget", () => {
    const { result } = renderHook(() =>
      usePresence({ awareness: null, role: "admin" }),
    );

    act(() => result.current.startFollowing(5, "Carol"));
    act(() => result.current.stopFollowing());
    expect(result.current.followTarget).toBeNull();
  });

  it("reportCursorMove calls setLocalCursorState", () => {
    const awareness = makeAwarenessMock();
    const { result } = renderHook(() =>
      usePresence({ awareness: awareness as unknown as Awareness, role: "admin" }),
    );

    act(() =>
      result.current.reportCursorMove(
        { line: 10, col: 5 },
        { anchor: 100, head: 110 },
      ),
    );

    expect(setLocalCursorState).toHaveBeenCalledWith(
      awareness,
      { line: 10, col: 5 },
      { anchor: 100, head: 110 },
    );
  });

  it("sets initial activity based on role", () => {
    const awareness = makeAwarenessMock();
    renderHook(() =>
      usePresence({ awareness: awareness as unknown as Awareness, role: "viewer" }),
    );
    expect(setLocalActivity).toHaveBeenCalledWith(awareness, "viewing");
  });

  it("sets editing activity for non-viewer roles", () => {
    const awareness = makeAwarenessMock();
    renderHook(() =>
      usePresence({ awareness: awareness as unknown as Awareness, role: "admin" }),
    );
    expect(setLocalActivity).toHaveBeenCalledWith(awareness, "editing");
  });

  it("follow target cleared when followed user disconnects", () => {
    const awareness = makeAwarenessMock();
    const carol = makeCollaborator({ clientId: 5, name: "Carol" });
    vi.mocked(getEnrichedCollaborators).mockReturnValue([carol]);

    const { result } = renderHook(() =>
      usePresence({ awareness: awareness as unknown as Awareness, role: "admin" }),
    );

    act(() => result.current.startFollowing(5, "Carol"));
    expect(result.current.followTarget).not.toBeNull();

    // Carol disconnects
    vi.mocked(getEnrichedCollaborators).mockReturnValue([]);
    act(() => awareness.emit("change"));

    expect(result.current.followTarget).toBeNull();
  });

  it("cleanup removes awareness listener", () => {
    const awareness = makeAwarenessMock();
    const { unmount } = renderHook(() =>
      usePresence({ awareness: awareness as unknown as Awareness, role: "admin" }),
    );

    expect(awareness._handlers.get("change")?.size).toBe(1);
    unmount();
    expect(awareness._handlers.get("change")?.size).toBe(0);
  });
});
