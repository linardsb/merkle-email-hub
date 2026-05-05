import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock lucide-react icons — explicit exports (Proxy causes vitest to hang)
vi.mock("lucide-react", () => {
  const makeIcon = (name: string) => (props: Record<string, unknown>) => (
    <svg data-testid={`icon-${name}`} {...props} />
  );
  return {
    AlertTriangle: makeIcon("AlertTriangle"),
    Inbox: makeIcon("Inbox"),
    FileX: makeIcon("FileX"),
    Search: makeIcon("Search"),
    Plus: makeIcon("Plus"),
  };
});

// Mock the shared UI Skeleton component
vi.mock("@email-hub/ui/components/ui/skeleton", () => ({
  Skeleton: ({ className }: { className?: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}));

// Mock type imports used by badge components
vi.mock("@/types/connectors", () => ({}));
vi.mock("@/types/design-sync", () => ({}));
vi.mock("@/types/figma", () => ({}));
vi.mock("@/types/briefs", () => ({}));

import { EmptyState } from "../ui/empty-state";
import { ErrorState } from "../ui/error-state";
import { ApprovalStatusBadge } from "../approvals/approval-status-badge";
import { ExportStatusBadge } from "../connectors/export-status-badge";
import { CompatibilityBadge } from "../components/compatibility-badge";
import {
  SkeletonCard,
  SkeletonStatsRow,
  SkeletonComponentCard,
  SkeletonSearchResult,
  SkeletonKnowledgeCard,
  SkeletonListItem,
} from "../ui/skeletons";
import { DesignStatusBadge } from "../design-sync/design-status-badge";
import { FigmaStatusBadge } from "../figma/figma-status-badge";
import { BriefStatusBadge } from "../briefs/brief-status-badge";
import { BriefPlatformBadge } from "../briefs/brief-platform-badge";

// ---------------------------------------------------------------------------
// 1. EmptyState
// ---------------------------------------------------------------------------
describe("EmptyState", () => {
  const MockIcon = (props: Record<string, unknown>) => <svg data-testid="mock-icon" {...props} />;

  it("renders the title", () => {
    render(<EmptyState icon={MockIcon as never} title="No items" />);
    expect(screen.getByText("No items")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(
      <EmptyState icon={MockIcon as never} title="No items" description="Create your first item" />,
    );
    expect(screen.getByText("Create your first item")).toBeInTheDocument();
  });

  it("does not render description when omitted", () => {
    const { container } = render(<EmptyState icon={MockIcon as never} title="No items" />);
    const paragraphs = container.querySelectorAll("p");
    expect(paragraphs).toHaveLength(1); // only title
  });

  it("renders action when provided", () => {
    render(
      <EmptyState icon={MockIcon as never} title="No items" action={<button>Add item</button>} />,
    );
    expect(screen.getByText("Add item")).toBeInTheDocument();
  });

  it("renders the icon", () => {
    render(<EmptyState icon={MockIcon as never} title="No items" />);
    expect(screen.getByTestId("mock-icon")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <EmptyState icon={MockIcon as never} title="No items" className="custom-class" />,
    );
    expect(container.firstChild).toHaveClass("custom-class");
  });
});

// ---------------------------------------------------------------------------
// 2. ErrorState
// ---------------------------------------------------------------------------
describe("ErrorState", () => {
  it("renders the error message", () => {
    render(<ErrorState message="Something went wrong" />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders retry button when onRetry is provided", () => {
    render(<ErrorState message="Error" onRetry={() => {}} />);
    expect(screen.getByText("Try again")).toBeInTheDocument();
  });

  it("calls onRetry when the retry button is clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Error" onRetry={onRetry} />);
    fireEvent.click(screen.getByText("Try again"));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("uses a custom retryLabel", () => {
    render(<ErrorState message="Error" onRetry={() => {}} retryLabel="Reload" />);
    expect(screen.getByText("Reload")).toBeInTheDocument();
  });

  it("hides the retry button when onRetry is not provided", () => {
    render(<ErrorState message="Error" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders the AlertTriangle icon", () => {
    render(<ErrorState message="Error" />);
    expect(screen.getByTestId("icon-AlertTriangle")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<ErrorState message="Error" className="my-error" />);
    expect(container.firstChild).toHaveClass("my-error");
  });
});

// ---------------------------------------------------------------------------
// 3. ApprovalStatusBadge
// ---------------------------------------------------------------------------
describe("ApprovalStatusBadge", () => {
  const cases: Array<[string, string]> = [
    ["pending", "Pending Review"],
    ["approved", "Approved"],
    ["rejected", "Rejected"],
    ["revision_requested", "Revision Requested"],
  ];

  it.each(cases)("renders '%s' as '%s'", (status, label) => {
    render(<ApprovalStatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("falls back to 'Pending Review' for an unknown status", () => {
    render(<ApprovalStatusBadge status="unknown_status" />);
    expect(screen.getByText("Pending Review")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 4. ExportStatusBadge
// ---------------------------------------------------------------------------
describe("ExportStatusBadge", () => {
  const cases: Array<[string, string]> = [
    ["success", "Success"],
    ["failed", "Failed"],
    ["exporting", "Exporting"],
  ];

  it.each(cases)("renders '%s' as '%s'", (status, label) => {
    render(<ExportStatusBadge status={status as "success" | "failed" | "exporting"} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 5. CompatibilityBadge
// ---------------------------------------------------------------------------
describe("CompatibilityBadge", () => {
  const cases: Array<[string, string]> = [
    ["full", "Full Support"],
    ["partial", "Partial"],
    ["issues", "Issues"],
  ];

  it.each(cases)("renders badge '%s' as '%s'", (badge, label) => {
    render(<CompatibilityBadge badge={badge} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("returns null when badge is null", () => {
    const { container } = render(<CompatibilityBadge badge={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("returns null when badge is undefined", () => {
    const { container } = render(<CompatibilityBadge badge={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows raw badge string for unknown values", () => {
    render(<CompatibilityBadge badge="experimental" />);
    expect(screen.getByText("experimental")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<CompatibilityBadge badge="full" className="extra" />);
    expect(screen.getByText("Full Support")).toHaveClass("extra");
  });
});

// ---------------------------------------------------------------------------
// 6. Skeletons
// ---------------------------------------------------------------------------
describe("SkeletonCard", () => {
  it("renders skeleton elements", () => {
    const { container } = render(<SkeletonCard />);
    const skeletons = container.querySelectorAll("[data-testid='skeleton']");
    expect(skeletons.length).toBeGreaterThanOrEqual(4);
  });
});

describe("SkeletonStatsRow", () => {
  it("renders 4 stat cards by default", () => {
    const { container } = render(<SkeletonStatsRow />);
    const cards = container.querySelectorAll(".rounded-lg");
    expect(cards).toHaveLength(4);
  });

  it("renders custom count of stat cards", () => {
    const { container } = render(<SkeletonStatsRow count={2} />);
    const cards = container.querySelectorAll(".rounded-lg");
    expect(cards).toHaveLength(2);
  });
});

describe("SkeletonComponentCard", () => {
  it("renders skeleton elements", () => {
    const { container } = render(<SkeletonComponentCard />);
    const skeletons = container.querySelectorAll("[data-testid='skeleton']");
    expect(skeletons.length).toBeGreaterThanOrEqual(2);
  });
});

describe("SkeletonSearchResult", () => {
  it("renders skeleton elements", () => {
    const { container } = render(<SkeletonSearchResult />);
    const skeletons = container.querySelectorAll("[data-testid='skeleton']");
    expect(skeletons.length).toBeGreaterThanOrEqual(5);
  });
});

describe("SkeletonKnowledgeCard", () => {
  it("renders skeleton elements", () => {
    const { container } = render(<SkeletonKnowledgeCard />);
    const skeletons = container.querySelectorAll("[data-testid='skeleton']");
    expect(skeletons.length).toBeGreaterThanOrEqual(5);
  });
});

describe("SkeletonListItem", () => {
  it("renders skeleton elements", () => {
    const { container } = render(<SkeletonListItem />);
    const skeletons = container.querySelectorAll("[data-testid='skeleton']");
    expect(skeletons.length).toBeGreaterThanOrEqual(2);
  });
});

// ---------------------------------------------------------------------------
// 7. DesignStatusBadge
// ---------------------------------------------------------------------------
describe("DesignStatusBadge", () => {
  const cases: Array<[string, string]> = [
    ["connected", "Connected"],
    ["syncing", "Syncing"],
    ["error", "Error"],
    ["disconnected", "Disconnected"],
  ];

  it.each(cases)("renders status '%s' as '%s'", (status, label) => {
    render(<DesignStatusBadge status={status as never} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 8. FigmaStatusBadge
// ---------------------------------------------------------------------------
describe("FigmaStatusBadge", () => {
  const cases: Array<[string, string]> = [
    ["connected", "Connected"],
    ["syncing", "Syncing"],
    ["error", "Error"],
    ["disconnected", "Disconnected"],
  ];

  it.each(cases)("renders status '%s' as '%s'", (status, label) => {
    render(<FigmaStatusBadge status={status as never} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 9. BriefStatusBadge
// ---------------------------------------------------------------------------
describe("BriefStatusBadge", () => {
  const cases: Array<[string, string]> = [
    ["connected", "Connected"],
    ["syncing", "Syncing"],
    ["error", "Error"],
    ["disconnected", "Disconnected"],
  ];

  it.each(cases)("renders status '%s' as '%s'", (status, label) => {
    render(<BriefStatusBadge status={status as never} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 10. BriefPlatformBadge
// ---------------------------------------------------------------------------
describe("BriefPlatformBadge", () => {
  const cases: Array<[string, string]> = [
    ["jira", "Jira"],
    ["asana", "Asana"],
    ["monday", "Monday.com"],
    ["clickup", "ClickUp"],
    ["trello", "Trello"],
    ["notion", "Notion"],
    ["wrike", "Wrike"],
    ["basecamp", "Basecamp"],
  ];

  it.each(cases)("renders platform '%s' as '%s'", (platform, label) => {
    render(<BriefPlatformBadge platform={platform as never} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("renders a colored dot for the platform", () => {
    const { container } = render(<BriefPlatformBadge platform={"jira" as never} />);
    const dot = container.querySelector("[aria-hidden='true']");
    expect(dot).toBeInTheDocument();
    expect(dot).toHaveStyle({ backgroundColor: "#2684FF" });
  });

  it("applies sm size by default", () => {
    render(<BriefPlatformBadge platform={"jira" as never} />);
    const badge = screen.getByText("Jira").closest("span");
    expect(badge?.className).toContain("text-xs");
  });

  it("applies md size when specified", () => {
    render(<BriefPlatformBadge platform={"jira" as never} size="md" />);
    const badge = screen.getByText("Jira").closest("span");
    expect(badge?.className).toContain("text-sm");
  });
});
