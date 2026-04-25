import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { Collaborator, FollowTarget, CollaborationStatus } from "@/types/collaboration";
import { PresencePanel } from "../presence-panel";
import { CollaborationBanner } from "../collaboration-banner";
import { ConflictResolver } from "../conflict-resolver";

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

describe("PresencePanel", () => {
  const defaultProps = {
    collaborators: [] as Collaborator[],
    followTarget: null as FollowTarget | null,
    onFollow: vi.fn(),
    onUnfollow: vi.fn(),
    onClose: vi.fn(),
  };

  it("renders empty state message", () => {
    render(<PresencePanel {...defaultProps} />);
    expect(screen.getByText("No one else is here")).toBeInTheDocument();
  });

  it("renders collaborator list", () => {
    const collaborators = [
      makeCollaborator({ clientId: 1, name: "Alice" }),
      makeCollaborator({ clientId: 2, name: "Bob" }),
    ];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("shows collaborator role", () => {
    const collaborators = [makeCollaborator({ role: "developer" })];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("Developer")).toBeInTheDocument();
  });

  it("shows activity indicator", () => {
    const collaborators = [makeCollaborator({ activity: "editing" })];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByLabelText("Editing")).toBeInTheDocument();
  });

  it("shows idle activity", () => {
    const collaborators = [makeCollaborator({ activity: "idle" })];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByLabelText("Idle")).toBeInTheDocument();
  });

  it("follow button calls onFollow", () => {
    const onFollow = vi.fn();
    const collaborators = [makeCollaborator({ clientId: 5, name: "Carol" })];
    render(<PresencePanel {...defaultProps} collaborators={collaborators} onFollow={onFollow} />);
    fireEvent.click(screen.getByText("Follow"));
    expect(onFollow).toHaveBeenCalledWith(5, "Carol");
  });

  it("followed user shows Following button that unfollows", () => {
    const onUnfollow = vi.fn();
    const collaborators = [makeCollaborator({ clientId: 5, name: "Carol" })];
    render(
      <PresencePanel
        {...defaultProps}
        collaborators={collaborators}
        followTarget={{ clientId: 5, name: "Carol" }}
        onUnfollow={onUnfollow}
      />,
    );
    fireEvent.click(screen.getByText("Following"));
    expect(onUnfollow).toHaveBeenCalled();
  });

  it("close button calls onClose", () => {
    const onClose = vi.fn();
    render(<PresencePanel {...defaultProps} onClose={onClose} />);
    // The close button is in the header
    const buttons = screen.getAllByRole("button");
    // First button should be the close button (X icon in header)
    fireEvent.click(buttons[0]!);
    expect(onClose).toHaveBeenCalled();
  });
});

describe("CollaborationBanner", () => {
  const defaultProps = {
    collaborators: [] as Collaborator[],
    status: "connected" as CollaborationStatus,
    onTogglePresencePanel: vi.fn(),
  };

  it("shows 'Only you' when no collaborators", () => {
    render(<CollaborationBanner {...defaultProps} />);
    expect(screen.getByText("Only you")).toBeInTheDocument();
  });

  it("shows editing count when users are editing", () => {
    const collaborators = [
      makeCollaborator({ activity: "editing" }),
      makeCollaborator({ clientId: 2, activity: "editing" }),
    ];
    render(<CollaborationBanner {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("2 editing")).toBeInTheDocument();
  });

  it("shows viewing count when no editors", () => {
    const collaborators = [makeCollaborator({ activity: "viewing" })];
    render(<CollaborationBanner {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("1 viewing")).toBeInTheDocument();
  });

  it("shows view-only badge when isViewOnly", () => {
    render(<CollaborationBanner {...defaultProps} isViewOnly />);
    expect(screen.getByText("View only")).toBeInTheDocument();
  });

  it("click toggles presence panel", () => {
    const onToggle = vi.fn();
    render(<CollaborationBanner {...defaultProps} onTogglePresencePanel={onToggle} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onToggle).toHaveBeenCalled();
  });

  it("shows avatar stack for collaborators", () => {
    const collaborators = [
      makeCollaborator({ clientId: 1, name: "Alice" }),
      makeCollaborator({ clientId: 2, name: "Bob" }),
    ];
    render(<CollaborationBanner {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
  });

  it("shows overflow count for many collaborators", () => {
    const collaborators = Array.from({ length: 5 }, (_, i) =>
      makeCollaborator({ clientId: i, name: `User${i}` }),
    );
    render(<CollaborationBanner {...defaultProps} collaborators={collaborators} />);
    expect(screen.getByText("+2")).toBeInTheDocument();
  });
});

describe("ConflictResolver", () => {
  const defaultProps = {
    hasConflict: true,
    onAccept: vi.fn(),
    onRevert: vi.fn(),
    onDismiss: vi.fn(),
  };

  it("renders nothing when no conflict", () => {
    const { container } = render(<ConflictResolver {...defaultProps} hasConflict={false} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders conflict banner with default description", () => {
    render(<ConflictResolver {...defaultProps} />);
    expect(screen.getByText(/Merge conflict detected/)).toBeInTheDocument();
  });

  it("renders custom conflict description", () => {
    render(
      <ConflictResolver {...defaultProps} conflictDescription="Section header was modified" />,
    );
    expect(screen.getByText("Section header was modified")).toBeInTheDocument();
  });

  it("Accept button calls onAccept", () => {
    const onAccept = vi.fn();
    render(<ConflictResolver {...defaultProps} onAccept={onAccept} />);
    fireEvent.click(screen.getByText("Accept"));
    expect(onAccept).toHaveBeenCalled();
  });

  it("Revert button calls onRevert", () => {
    const onRevert = vi.fn();
    render(<ConflictResolver {...defaultProps} onRevert={onRevert} />);
    fireEvent.click(screen.getByText("Revert to mine"));
    expect(onRevert).toHaveBeenCalled();
  });

  it("Dismiss button calls onDismiss", () => {
    const onDismiss = vi.fn();
    render(<ConflictResolver {...defaultProps} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText("Dismiss conflict"));
    expect(onDismiss).toHaveBeenCalled();
  });
});
