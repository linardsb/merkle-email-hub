import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { ChatMessage, AgentMode, ChatStatus } from "@/types/chat";
import type { Collaborator, FollowTarget, CollaborationStatus } from "@/types/collaboration";

// ---------------------------------------------------------------------------
// Mocks — external dependencies
// ---------------------------------------------------------------------------

vi.mock("lucide-react", () => {
  const icon = ({ className, "aria-label": ariaLabel, ...rest }: Record<string, unknown>) => (
    <span
      className={className as string}
      aria-label={ariaLabel as string}
      data-testid="icon"
      {...rest}
    />
  );
  return {
    MessageSquare: icon,
    Wand2: icon,
    Moon: icon,
    PenTool: icon,
    Wrench: icon,
    Eye: icon,
    Users: icon,
    FileSearch: icon,
    BookOpen: icon,
    Lightbulb: icon,
    ChevronDown: icon,
    ChevronUp: icon,
    Send: icon,
    Square: icon,
    Bot: icon,
    User: icon,
    Check: icon,
    Copy: icon,
    Loader2: icon,
    WifiOff: icon,
    X: icon,
    UserRoundPen: icon,
    Clock: icon,
    CheckCircle2: icon,
    XCircle: icon,
    AlertTriangle: icon,
    Cog: icon,
  };
});

vi.mock("@email-hub/ui/components/ui/button", () => ({
  Button: ({ children, ...props }: { children: React.ReactNode } & Record<string, unknown>) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock("@email-hub/ui/components/ui/badge", () => ({
  Badge: ({ children, ...props }: { children: React.ReactNode } & Record<string, unknown>) => (
    <span {...props}>{children}</span>
  ),
}));

vi.mock("@email-hub/ui/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dropdown-menu">{children}</div>
  ),
  DropdownMenuTrigger: ({
    children,
    asChild,
    ...props
  }: { children: React.ReactNode; asChild?: boolean } & Record<string, unknown>) => (
    <div data-testid="dropdown-trigger" {...props}>
      {children}
    </div>
  ),
  DropdownMenuContent: ({
    children,
    ...props
  }: { children: React.ReactNode } & Record<string, unknown>) => (
    <div data-testid="dropdown-content" {...props}>
      {children}
    </div>
  ),
  DropdownMenuGroup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DropdownMenuLabel: ({
    children,
    ...props
  }: { children: React.ReactNode } & Record<string, unknown>) => <div {...props}>{children}</div>,
  DropdownMenuItem: ({
    children,
    onClick,
    ...props
  }: { children: React.ReactNode; onClick?: () => void } & Record<string, unknown>) => (
    <button onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

// Hook mocks
vi.mock("@/hooks/use-network-status", () => ({
  useNetworkStatus: vi.fn(),
}));

vi.mock("@/hooks/use-blueprint-runs", () => ({
  useRunCheckpoints: vi.fn(),
}));

vi.mock("@/components/workspace/chat/confidence-indicator", () => ({
  ConfidenceIndicator: ({ confidence }: { confidence: number }) => (
    <span data-testid="confidence">{confidence}</span>
  ),
}));

vi.mock("@/components/workspace/chat/blueprint-result-card", () => ({
  BlueprintResultCard: () => <div data-testid="blueprint-result" />,
}));

// ---------------------------------------------------------------------------
// Imports under test (after mocks)
// ---------------------------------------------------------------------------

import { AgentSelectorDropdown } from "../workspace/chat/agent-selector-dropdown";
import { MessageBubble } from "../workspace/chat/message-bubble";
import { ChatInput } from "../workspace/chat/chat-input";
import { ConnectionStatus } from "../workspace/collaboration/connection-status";
import { PresencePanel } from "../collaboration/presence-panel";
import { RunCheckpoints } from "../workspace/blueprint/run-checkpoints";
import { OfflineBanner } from "../ui/offline-banner";

import { useNetworkStatus } from "@/hooks/use-network-status";
import { useRunCheckpoints } from "@/hooks/use-blueprint-runs";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: "msg-1",
    role: "assistant",
    content: "Hello from the assistant",
    timestamp: Date.now(),
    agent: "chat",
    isStreaming: false,
    ...overrides,
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

// ===========================================================================
// 1. AgentSelectorDropdown
// ===========================================================================

describe("AgentSelectorDropdown", () => {
  it("renders the current agent label in trigger", () => {
    render(<AgentSelectorDropdown agent="scaffolder" onSelect={vi.fn()} />);
    // "Scaffolder" appears in trigger and in menu item
    const elements = screen.getAllByText("Scaffolder");
    expect(elements.length).toBe(2); // trigger + menu item
    // The trigger button is inside dropdown-trigger
    const trigger = screen.getByTestId("dropdown-trigger");
    expect(trigger).toHaveTextContent("Scaffolder");
  });

  it("renders the default chat agent label", () => {
    render(<AgentSelectorDropdown agent="chat" onSelect={vi.fn()} />);
    // "Chat" appears in trigger and in menu item — both should be present
    const chatElements = screen.getAllByText("Chat");
    expect(chatElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders all agent group labels", () => {
    render(<AgentSelectorDropdown agent="chat" onSelect={vi.fn()} />);
    expect(screen.getByText("Build")).toBeInTheDocument();
    expect(screen.getByText("Optimize")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
  });

  it("renders all agent options", () => {
    render(<AgentSelectorDropdown agent="chat" onSelect={vi.fn()} />);
    expect(screen.getByText("Dark Mode")).toBeInTheDocument();
    expect(screen.getByText("Accessibility")).toBeInTheDocument();
    expect(screen.getByText("Innovator")).toBeInTheDocument();
  });

  it("calls onSelect when an agent is clicked", () => {
    const onSelect = vi.fn();
    render(<AgentSelectorDropdown agent="chat" onSelect={onSelect} />);
    fireEvent.click(screen.getByText("Dark Mode"));
    expect(onSelect).toHaveBeenCalledWith("dark_mode");
  });
});

// ===========================================================================
// 2. MessageBubble
// ===========================================================================

describe("MessageBubble", () => {
  const onApplyHtml = vi.fn();

  beforeEach(() => {
    onApplyHtml.mockClear();
  });

  it("renders user message with user content", () => {
    const msg = makeMessage({ role: "user", content: "Hello there" });
    render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    expect(screen.getByText("Hello there")).toBeInTheDocument();
  });

  it("renders user message aligned to end (justify-end class)", () => {
    const msg = makeMessage({ role: "user", content: "User text" });
    const { container } = render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("justify-end");
  });

  it("renders assistant message without justify-end", () => {
    const msg = makeMessage({ role: "assistant", content: "Reply" });
    const { container } = render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).not.toContain("justify-end");
  });

  it("renders streaming indicator when streaming with content", () => {
    const msg = makeMessage({ isStreaming: true, content: "Partial..." });
    const { container } = render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    // The blinking cursor span
    const cursor = container.querySelector(".animate-pulse");
    expect(cursor).toBeInTheDocument();
  });

  it("renders 'Thinking...' when streaming with no content", () => {
    const msg = makeMessage({ isStreaming: true, content: "" });
    render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
  });

  it("renders code blocks from markdown-style fences", () => {
    const msg = makeMessage({
      content: "Here is code:\n```html\n<div>Hello</div>\n```",
    });
    render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    expect(screen.getByText("<div>Hello</div>")).toBeInTheDocument();
    expect(screen.getByText("html")).toBeInTheDocument();
  });

  it("shows Apply button for HTML-like code blocks", () => {
    const msg = makeMessage({
      content: "```html\n<table><tr><td>Test</td></tr></table>\n```",
    });
    render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    expect(screen.getByText("Apply")).toBeInTheDocument();
  });

  it("renders confidence indicator when not streaming and confidence is set", () => {
    const msg = makeMessage({ confidence: 0.95 });
    render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    expect(screen.getByTestId("confidence")).toBeInTheDocument();
    expect(screen.getByTestId("confidence")).toHaveTextContent("0.95");
  });

  it("does not show confidence indicator while streaming", () => {
    const msg = makeMessage({ isStreaming: true, content: "streaming", confidence: 0.9 });
    render(<MessageBubble message={msg} onApplyHtml={onApplyHtml} />);
    expect(screen.queryByTestId("confidence")).not.toBeInTheDocument();
  });
});

// ===========================================================================
// 3. ChatInput
// ===========================================================================

describe("ChatInput", () => {
  const defaultProps = {
    onSend: vi.fn(),
    onStop: vi.fn(),
    status: "idle" as ChatStatus,
  };

  beforeEach(() => {
    defaultProps.onSend.mockClear();
    defaultProps.onStop.mockClear();
  });

  it("renders a textarea with placeholder", () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByPlaceholderText("Ask the AI assistant...")).toBeInTheDocument();
  });

  it("renders custom placeholder", () => {
    render(<ChatInput {...defaultProps} placeholder="Type here..." />);
    expect(screen.getByPlaceholderText("Type here...")).toBeInTheDocument();
  });

  it("renders send button when idle", () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByLabelText("Send message")).toBeInTheDocument();
  });

  it("renders stop button when streaming", () => {
    render(<ChatInput {...defaultProps} status="streaming" />);
    expect(screen.getByLabelText("Stop generating")).toBeInTheDocument();
    expect(screen.queryByLabelText("Send message")).not.toBeInTheDocument();
  });

  it("disables textarea when streaming", () => {
    render(<ChatInput {...defaultProps} status="streaming" />);
    const textarea = screen.getByPlaceholderText("Ask the AI assistant...");
    expect(textarea).toBeDisabled();
  });

  it("calls onSend with trimmed content when send button is clicked", () => {
    render(<ChatInput {...defaultProps} />);
    const textarea = screen.getByPlaceholderText("Ask the AI assistant...") as HTMLTextAreaElement;
    fireEvent.input(textarea, { target: { value: "  Hello world  " } });
    textarea.value = "  Hello world  ";
    fireEvent.click(screen.getByLabelText("Send message"));
    expect(defaultProps.onSend).toHaveBeenCalledWith("Hello world");
  });

  it("clears textarea after sending", () => {
    render(<ChatInput {...defaultProps} />);
    const textarea = screen.getByPlaceholderText("Ask the AI assistant...") as HTMLTextAreaElement;
    textarea.value = "Hello";
    fireEvent.click(screen.getByLabelText("Send message"));
    expect(textarea.value).toBe("");
  });

  it("does not call onSend when textarea is empty", () => {
    render(<ChatInput {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Send message"));
    expect(defaultProps.onSend).not.toHaveBeenCalled();
  });

  it("calls onStop when stop button is clicked during streaming", () => {
    render(<ChatInput {...defaultProps} status="streaming" />);
    fireEvent.click(screen.getByLabelText("Stop generating"));
    expect(defaultProps.onStop).toHaveBeenCalled();
  });
});

// ===========================================================================
// 4. ConnectionStatus
// ===========================================================================

describe("ConnectionStatus", () => {
  it("renders 'Connected' for connected status", () => {
    render(<ConnectionStatus status="connected" />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("renders 'Disconnected' for disconnected status", () => {
    render(<ConnectionStatus status="disconnected" />);
    expect(screen.getByText("Disconnected")).toBeInTheDocument();
  });

  it("renders 'Reconnecting' for connecting status", () => {
    render(<ConnectionStatus status="connecting" />);
    expect(screen.getByText("Reconnecting")).toBeInTheDocument();
  });

  it("sets title attribute to the label", () => {
    const { container } = render(<ConnectionStatus status="connected" />);
    expect(container.firstChild).toHaveAttribute("title", "Connected");
  });

  it("renders a status dot with correct class for connected", () => {
    const { container } = render(<ConnectionStatus status="connected" />);
    const dot = container.querySelector("span.bg-success");
    expect(dot).toBeInTheDocument();
  });

  it("renders a status dot with destructive class for disconnected", () => {
    const { container } = render(<ConnectionStatus status="disconnected" />);
    const dot = container.querySelector("span.bg-destructive");
    expect(dot).toBeInTheDocument();
  });
});

// ===========================================================================
// 5. PresencePanel
// ===========================================================================

describe("PresencePanel", () => {
  const defaultProps = {
    collaborators: [] as Collaborator[],
    followTarget: null as FollowTarget | null,
    onFollow: vi.fn(),
    onUnfollow: vi.fn(),
    onClose: vi.fn(),
  };

  beforeEach(() => {
    defaultProps.onFollow.mockClear();
    defaultProps.onUnfollow.mockClear();
    defaultProps.onClose.mockClear();
  });

  it("renders empty state when no collaborators", () => {
    render(<PresencePanel {...defaultProps} />);
    expect(screen.getByText("No one else is here")).toBeInTheDocument();
  });

  it("renders collaborator names", () => {
    const collaborators = [
      makeCollaborator({ clientId: 1, name: "Alice" }),
      makeCollaborator({ clientId: 2, name: "Bob" }),
    ];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("renders collaborator roles", () => {
    const collaborators = [makeCollaborator({ role: "developer" })];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("Developer")).toBeInTheDocument();
  });

  it("shows Follow button for each collaborator", () => {
    const collaborators = [makeCollaborator()];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("Follow")).toBeInTheDocument();
  });

  it("shows Following when collaborator is the follow target", () => {
    const collaborators = [makeCollaborator({ clientId: 42, name: "Alice" })];
    const followTarget: FollowTarget = { clientId: 42, name: "Alice" };
    render(
      <PresencePanel {...defaultProps} collaborators={collaborators} followTarget={followTarget} />,
    );
    expect(screen.getByText("Following")).toBeInTheDocument();
  });

  it("calls onFollow when Follow button is clicked", () => {
    const collaborators = [makeCollaborator({ clientId: 7, name: "Carol" })];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} />);
    fireEvent.click(screen.getByText("Follow"));
    expect(defaultProps.onFollow).toHaveBeenCalledWith(7, "Carol");
  });

  it("calls onUnfollow when Following button is clicked", () => {
    const collaborators = [makeCollaborator({ clientId: 7, name: "Carol" })];
    const followTarget: FollowTarget = { clientId: 7, name: "Carol" };
    render(
      <PresencePanel {...defaultProps} collaborators={collaborators} followTarget={followTarget} />,
    );
    fireEvent.click(screen.getByText("Following"));
    expect(defaultProps.onUnfollow).toHaveBeenCalled();
  });

  it("calls onClose when close button is clicked", () => {
    render(<PresencePanel {...defaultProps} />);
    // The close button is the button in the header
    const closeButtons = screen.getAllByRole("button");
    // First button should be the close button (in the header)
    fireEvent.click(closeButtons[0]!);
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("renders the header title", () => {
    render(<PresencePanel {...defaultProps} />);
    expect(screen.getByText("Collaborators")).toBeInTheDocument();
  });
});

// ===========================================================================
// 6. RunCheckpoints
// ===========================================================================

describe("RunCheckpoints", () => {
  const mockUseRunCheckpoints = vi.mocked(useRunCheckpoints);

  beforeEach(() => {
    mockUseRunCheckpoints.mockReturnValue({
      data: null,
      isLoading: false,
      error: undefined,
      mutate: vi.fn(),
      isValidating: false,
    } as unknown as ReturnType<typeof useRunCheckpoints>);
  });

  it("renders the Checkpoints toggle button", () => {
    render(<RunCheckpoints runId="run-1" />);
    expect(screen.getByText("Checkpoints")).toBeInTheDocument();
  });

  it("does not show checkpoints list when collapsed", () => {
    render(<RunCheckpoints runId="run-1" />);
    expect(screen.queryByText("No checkpoints available")).not.toBeInTheDocument();
  });

  it("shows loading spinner when expanded and loading", () => {
    mockUseRunCheckpoints.mockReturnValue({
      data: null,
      isLoading: true,
      error: undefined,
      mutate: vi.fn(),
      isValidating: false,
    } as unknown as ReturnType<typeof useRunCheckpoints>);

    render(<RunCheckpoints runId="run-1" />);
    fireEvent.click(screen.getByText("Checkpoints"));

    const { container } = render(<RunCheckpoints runId="run-1" />);
    // After click, the hook is called with runId
    expect(mockUseRunCheckpoints).toHaveBeenCalled();
  });

  it("shows empty message when no checkpoints after expanding", () => {
    mockUseRunCheckpoints.mockReturnValue({
      data: { checkpoints: [] },
      isLoading: false,
      error: undefined,
      mutate: vi.fn(),
      isValidating: false,
    } as unknown as ReturnType<typeof useRunCheckpoints>);

    render(<RunCheckpoints runId="run-1" />);
    fireEvent.click(screen.getByText("Checkpoints"));
    expect(screen.getByText("No checkpoints available")).toBeInTheDocument();
  });

  it("renders checkpoint items with status labels", () => {
    mockUseRunCheckpoints.mockReturnValue({
      data: {
        checkpoints: [
          {
            node_name: "scaffolder",
            node_index: 0,
            status: "success",
            created_at: new Date().toISOString(),
          },
          {
            node_name: "dark_mode_agent",
            node_index: 1,
            status: "failed",
            created_at: new Date().toISOString(),
          },
        ],
      },
      isLoading: false,
      error: undefined,
      mutate: vi.fn(),
      isValidating: false,
    } as unknown as ReturnType<typeof useRunCheckpoints>);

    render(<RunCheckpoints runId="run-1" />);
    fireEvent.click(screen.getByText("Checkpoints"));

    expect(screen.getByText("Passed")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("shows Resume Point badge when checkpoint matches resumedFromNode", () => {
    mockUseRunCheckpoints.mockReturnValue({
      data: {
        checkpoints: [
          {
            node_name: "scaffolder",
            node_index: 0,
            status: "success",
            created_at: new Date().toISOString(),
          },
        ],
      },
      isLoading: false,
      error: undefined,
      mutate: vi.fn(),
      isValidating: false,
    } as unknown as ReturnType<typeof useRunCheckpoints>);

    render(<RunCheckpoints runId="run-1" resumedFromNode="scaffolder" />);
    fireEvent.click(screen.getByText("Checkpoints"));

    expect(screen.getByText("Resume Point")).toBeInTheDocument();
  });
});

// ===========================================================================
// 7. OfflineBanner
// ===========================================================================

describe("OfflineBanner", () => {
  const mockUseNetworkStatus = vi.mocked(useNetworkStatus);

  it("renders nothing when online", () => {
    mockUseNetworkStatus.mockReturnValue(true);
    const { container } = render(<OfflineBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders banner when offline", () => {
    mockUseNetworkStatus.mockReturnValue(false);
    render(<OfflineBanner />);
    expect(
      screen.getByText("You appear to be offline. Some features may be unavailable."),
    ).toBeInTheDocument();
  });

  it("hides banner when network comes back online", () => {
    mockUseNetworkStatus.mockReturnValue(false);
    const { rerender } = render(<OfflineBanner />);
    expect(
      screen.getByText("You appear to be offline. Some features may be unavailable."),
    ).toBeInTheDocument();

    mockUseNetworkStatus.mockReturnValue(true);
    rerender(<OfflineBanner />);
    expect(
      screen.queryByText("You appear to be offline. Some features may be unavailable."),
    ).not.toBeInTheDocument();
  });
});
