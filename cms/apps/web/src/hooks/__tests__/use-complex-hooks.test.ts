// @ts-nocheck
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// ---------------------------------------------------------------------------
// 1. useNetworkStatus
// ---------------------------------------------------------------------------

describe("useNetworkStatus", () => {
  let onlineGetter: ReturnType<typeof vi.spyOn>;
  const listeners: Record<string, Set<EventListener>> = {};

  beforeEach(() => {
    listeners["online"] = new Set();
    listeners["offline"] = new Set();

    vi.spyOn(window, "addEventListener").mockImplementation(
      (event: string, handler: EventListenerOrEventListenerObject) => {
        if (event in listeners) {
          listeners[event].add(handler as EventListener);
        }
      },
    );

    vi.spyOn(window, "removeEventListener").mockImplementation(
      (event: string, handler: EventListenerOrEventListenerObject) => {
        listeners[event]?.delete(handler as EventListener);
      },
    );

    onlineGetter = vi.spyOn(navigator, "onLine", "get");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns true when navigator.onLine is true", async () => {
    onlineGetter.mockReturnValue(true);

    const { useNetworkStatus } = await import("@/hooks/use-network-status");
    const { result } = renderHook(() => useNetworkStatus());

    expect(result.current).toBe(true);
  });

  it("returns false when navigator.onLine is false", async () => {
    onlineGetter.mockReturnValue(false);

    const { useNetworkStatus } = await import("@/hooks/use-network-status");
    const { result } = renderHook(() => useNetworkStatus());

    expect(result.current).toBe(false);
  });

  it("subscribes to online and offline events", async () => {
    onlineGetter.mockReturnValue(true);

    const { useNetworkStatus } = await import("@/hooks/use-network-status");
    renderHook(() => useNetworkStatus());

    expect(listeners["online"].size).toBe(1);
    expect(listeners["offline"].size).toBe(1);
  });

  it("updates when going offline", async () => {
    onlineGetter.mockReturnValue(true);

    const { useNetworkStatus } = await import("@/hooks/use-network-status");
    const { result } = renderHook(() => useNetworkStatus());

    expect(result.current).toBe(true);

    // Simulate going offline
    onlineGetter.mockReturnValue(false);
    act(() => {
      listeners["offline"].forEach((h) => h(new Event("offline")));
    });

    expect(result.current).toBe(false);
  });

  it("updates when coming back online", async () => {
    onlineGetter.mockReturnValue(false);

    const { useNetworkStatus } = await import("@/hooks/use-network-status");
    const { result } = renderHook(() => useNetworkStatus());

    expect(result.current).toBe(false);

    onlineGetter.mockReturnValue(true);
    act(() => {
      listeners["online"].forEach((h) => h(new Event("online")));
    });

    expect(result.current).toBe(true);
  });

  it("cleans up event listeners on unmount", async () => {
    onlineGetter.mockReturnValue(true);

    const { useNetworkStatus } = await import("@/hooks/use-network-status");
    const { unmount } = renderHook(() => useNetworkStatus());

    expect(listeners["online"].size).toBe(1);
    expect(listeners["offline"].size).toBe(1);

    unmount();

    expect(listeners["online"].size).toBe(0);
    expect(listeners["offline"].size).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 2. useWorkspaceShortcuts
// ---------------------------------------------------------------------------

describe("useWorkspaceShortcuts", () => {
  let keydownHandlers: Set<EventListener>;

  beforeEach(() => {
    keydownHandlers = new Set();

    vi.spyOn(document, "addEventListener").mockImplementation(
      (event: string, handler: EventListenerOrEventListenerObject) => {
        if (event === "keydown") {
          keydownHandlers.add(handler as EventListener);
        }
      },
    );

    vi.spyOn(document, "removeEventListener").mockImplementation(
      (event: string, handler: EventListenerOrEventListenerObject) => {
        if (event === "keydown") {
          keydownHandlers.delete(handler as EventListener);
        }
      },
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function fireKey(key: string, opts: Partial<KeyboardEventInit> = {}) {
    const event = new KeyboardEvent("keydown", {
      key,
      metaKey: true,
      bubbles: true,
      cancelable: true,
      ...opts,
    });
    vi.spyOn(event, "preventDefault");
    keydownHandlers.forEach((h) => h(event));
    return event;
  }

  it("registers a keydown listener on mount", async () => {
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({}));

    expect(keydownHandlers.size).toBe(1);
  });

  it("removes the keydown listener on unmount", async () => {
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    const { unmount } = renderHook(() => useWorkspaceShortcuts({}));

    expect(keydownHandlers.size).toBe(1);
    unmount();
    expect(keydownHandlers.size).toBe(0);
  });

  it("calls onSave on Cmd+S", async () => {
    const onSave = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onSave }));

    const event = fireKey("s");
    expect(onSave).toHaveBeenCalledOnce();
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("calls onGenerate on Cmd+Shift+G", async () => {
    const onGenerate = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onGenerate }));

    const event = fireKey("g", { shiftKey: true });
    expect(onGenerate).toHaveBeenCalledOnce();
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("calls onRunQA on Cmd+Shift+Q", async () => {
    const onRunQA = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onRunQA }));

    const event = fireKey("q", { shiftKey: true });
    expect(onRunQA).toHaveBeenCalledOnce();
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("calls onExport on Cmd+Shift+E", async () => {
    const onExport = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onExport }));

    const event = fireKey("e", { shiftKey: true });
    expect(onExport).toHaveBeenCalledOnce();
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("calls onToggleChat on Cmd+B", async () => {
    const onToggleChat = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onToggleChat }));

    const event = fireKey("b");
    expect(onToggleChat).toHaveBeenCalledOnce();
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("calls onToggleSidebar on Cmd+J", async () => {
    const onToggleSidebar = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onToggleSidebar }));

    const event = fireKey("j");
    expect(onToggleSidebar).toHaveBeenCalledOnce();
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("calls onToggleView on Cmd+Shift+V", async () => {
    const onToggleView = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onToggleView }));

    const event = fireKey("v", { shiftKey: true });
    expect(onToggleView).toHaveBeenCalledOnce();
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("ignores keys without modifier", async () => {
    const onSave = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onSave }));

    fireKey("s", { metaKey: false, ctrlKey: false });
    expect(onSave).not.toHaveBeenCalled();
  });

  it("does not throw when callback is undefined", async () => {
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({}));

    // Should not throw even with no callbacks registered
    expect(() => fireKey("s")).not.toThrow();
    expect(() => fireKey("g", { shiftKey: true })).not.toThrow();
  });

  it("works with ctrlKey instead of metaKey", async () => {
    const onSave = vi.fn();
    const { useWorkspaceShortcuts } = await import("@/hooks/use-workspace-shortcuts");
    renderHook(() => useWorkspaceShortcuts({ onSave }));

    fireKey("s", { metaKey: false, ctrlKey: true });
    expect(onSave).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// 3. useChatHistory
// ---------------------------------------------------------------------------

describe("useChatHistory", () => {
  let storage: Record<string, string>;

  beforeEach(() => {
    storage = {};

    vi.stubGlobal("localStorage", {
      getItem: vi.fn((key: string) => storage[key] ?? null),
      setItem: vi.fn((key: string, value: string) => {
        storage[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete storage[key];
      }),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  function makeChatMessage(
    overrides: Partial<{
      id: string;
      role: "user" | "assistant";
      content: string;
      timestamp: number;
      agent: string;
    }> = {},
  ) {
    return {
      id: overrides.id ?? `msg-${Date.now()}`,
      role: overrides.role ?? "user",
      content: overrides.content ?? "Hello",
      timestamp: overrides.timestamp ?? Date.now(),
      agent: overrides.agent ?? "chat",
      isStreaming: false,
    };
  }

  it("starts with empty sessions when localStorage is empty", async () => {
    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    expect(result.current.sessions).toEqual([]);
  });

  it("loads existing sessions from localStorage", async () => {
    const existingSession = {
      id: "session-1",
      projectId: "project-1",
      agent: "chat",
      messages: [makeChatMessage({ content: "Hi" })],
      createdAt: 1000,
      updatedAt: 2000,
      messageCount: 1,
      preview: "Hi",
    };
    storage["chat-history-project-1"] = JSON.stringify([existingSession]);

    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    expect(result.current.sessions).toHaveLength(1);
    expect(result.current.sessions[0]!.id).toBe("session-1");
  });

  it("saveSession adds a session to the front of the list", async () => {
    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    const messages = [
      makeChatMessage({ role: "user", content: "Hello world", timestamp: 100 }),
      makeChatMessage({
        role: "assistant",
        content: "Hi there!",
        timestamp: 200,
      }),
    ];

    act(() => {
      result.current.saveSession(messages, "chat");
    });

    expect(result.current.sessions).toHaveLength(1);
    const session = result.current.sessions[0]!;
    expect(session.projectId).toBe("project-1");
    expect(session.agent).toBe("chat");
    expect(session.messageCount).toBe(2);
    expect(session.preview).toBe("Hello world");
    expect(session.createdAt).toBe(100);
    expect(session.updatedAt).toBe(200);
  });

  it("saveSession does nothing with empty messages array", async () => {
    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    act(() => {
      result.current.saveSession([], "chat");
    });

    expect(result.current.sessions).toHaveLength(0);
  });

  it("saveSession uses first message content as preview when no user message", async () => {
    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    const messages = [
      makeChatMessage({
        role: "assistant",
        content: "System initialized",
        timestamp: 100,
      }),
    ];

    act(() => {
      result.current.saveSession(messages, "chat");
    });

    expect(result.current.sessions[0]!.preview).toBe("System initialized");
  });

  it("saveSession caps sessions at MAX_SESSIONS (20)", async () => {
    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    // Add 21 sessions
    for (let i = 0; i < 21; i++) {
      act(() => {
        result.current.saveSession(
          [makeChatMessage({ content: `Msg ${i}`, timestamp: i * 100 })],
          "chat",
        );
      });
    }

    expect(result.current.sessions).toHaveLength(20);
    // Most recent should be first
    expect(result.current.sessions[0]!.preview).toBe("Msg 20");
  });

  it("deleteSession removes the specified session", async () => {
    const existingSession = {
      id: "session-to-delete",
      projectId: "project-1",
      agent: "chat",
      messages: [makeChatMessage()],
      createdAt: 1000,
      updatedAt: 2000,
      messageCount: 1,
      preview: "Hello",
    };
    storage["chat-history-project-1"] = JSON.stringify([existingSession]);

    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    expect(result.current.sessions).toHaveLength(1);

    act(() => {
      result.current.deleteSession("session-to-delete");
    });

    expect(result.current.sessions).toHaveLength(0);
  });

  it("clearAllSessions empties the list", async () => {
    const sessions = [
      {
        id: "s1",
        projectId: "project-1",
        agent: "chat",
        messages: [],
        createdAt: 1000,
        updatedAt: 2000,
        messageCount: 0,
        preview: "",
      },
      {
        id: "s2",
        projectId: "project-1",
        agent: "chat",
        messages: [],
        createdAt: 1000,
        updatedAt: 2000,
        messageCount: 0,
        preview: "",
      },
    ];
    storage["chat-history-project-1"] = JSON.stringify(sessions);

    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    expect(result.current.sessions).toHaveLength(2);

    act(() => {
      result.current.clearAllSessions();
    });

    expect(result.current.sessions).toHaveLength(0);
  });

  it("persists sessions to localStorage on change", async () => {
    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    act(() => {
      result.current.saveSession(
        [makeChatMessage({ content: "Persisted", timestamp: 100 })],
        "chat",
      );
    });

    expect(localStorage.setItem).toHaveBeenCalledWith("chat-history-project-1", expect.any(String));

    const persisted = JSON.parse(storage["chat-history-project-1"]!);
    expect(persisted).toHaveLength(1);
    expect(persisted[0].preview).toBe("Persisted");
  });

  it("handles corrupted localStorage gracefully", async () => {
    storage["chat-history-project-1"] = "not-valid-json{{{";

    const { useChatHistory } = await import("@/hooks/use-chat-history");
    const { result } = renderHook(() => useChatHistory("project-1"));

    // Should fall back to empty array
    expect(result.current.sessions).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// 4. useChat
// ---------------------------------------------------------------------------

// useChat is tightly coupled to authFetch (SSE streaming), dynamic imports
// for demo mode, and complex async streaming state. We mock authFetch to test
// the core state management (initial state, clearMessages, replaceMessages,
// stopStreaming). Full SSE streaming tests would require an elaborate
// ReadableStream mock and are better suited for integration tests.

vi.mock("@/lib/auth-fetch", () => ({
  authFetch: vi.fn(),
  LONG_TIMEOUT_MS: 120_000,
}));

vi.mock("@/lib/confidence", () => ({
  extractConfidence: vi.fn(() => null),
  stripConfidenceComment: vi.fn((s: string) => s),
}));

describe("useChat", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8891");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("starts with idle status and empty messages", async () => {
    const { useChat } = await import("@/hooks/use-chat");
    const { result } = renderHook(() => useChat("project-1"));

    expect(result.current.messages).toEqual([]);
    expect(result.current.status).toBe("idle");
    expect(result.current.error).toBeNull();
    expect(result.current.blueprintRunning).toBe(false);
  });

  it("clearMessages resets all state", async () => {
    const { useChat } = await import("@/hooks/use-chat");
    const { result } = renderHook(() => useChat("project-1"));

    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.status).toBe("idle");
    expect(result.current.error).toBeNull();
  });

  it("replaceMessages sets messages and resets status", async () => {
    const { useChat } = await import("@/hooks/use-chat");
    const { result } = renderHook(() => useChat("project-1"));

    const newMessages = [
      {
        id: "msg-1",
        role: "user" as const,
        content: "Hello",
        timestamp: Date.now(),
        agent: "chat" as const,
        isStreaming: false,
      },
      {
        id: "msg-2",
        role: "assistant" as const,
        content: "Hi there!",
        timestamp: Date.now(),
        agent: "chat" as const,
        isStreaming: false,
      },
    ];

    act(() => {
      result.current.replaceMessages(newMessages);
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]!.content).toBe("Hello");
    expect(result.current.messages[1]!.content).toBe("Hi there!");
    expect(result.current.status).toBe("idle");
    expect(result.current.error).toBeNull();
  });

  it("sendMessage ignores empty/whitespace content", async () => {
    const { useChat } = await import("@/hooks/use-chat");
    const { result } = renderHook(() => useChat("project-1"));

    act(() => {
      result.current.sendMessage("   ", "chat");
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.status).toBe("idle");
  });

  it("stopStreaming marks streaming messages as not streaming", async () => {
    const { useChat } = await import("@/hooks/use-chat");
    const { result } = renderHook(() => useChat("project-1"));

    // Manually set up messages with a streaming one via replaceMessages
    const messagesWithStreaming = [
      {
        id: "msg-1",
        role: "user" as const,
        content: "Hello",
        timestamp: Date.now(),
        agent: "chat" as const,
        isStreaming: false,
      },
      {
        id: "msg-2",
        role: "assistant" as const,
        content: "Partial response...",
        timestamp: Date.now(),
        agent: "chat" as const,
        isStreaming: true,
      },
    ];

    act(() => {
      result.current.replaceMessages(messagesWithStreaming);
    });

    // Note: replaceMessages doesn't preserve isStreaming — it just sets messages.
    // stopStreaming sets status to idle and marks all streaming messages as done.
    act(() => {
      result.current.stopStreaming();
    });

    expect(result.current.status).toBe("idle");
    // After stopStreaming, any messages with isStreaming=true should be marked false
    const streamingMessages = result.current.messages.filter((m) => m.isStreaming);
    expect(streamingMessages).toHaveLength(0);
  });
});
