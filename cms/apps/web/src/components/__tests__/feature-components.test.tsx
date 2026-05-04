import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks — hooks and external dependencies
// ---------------------------------------------------------------------------

vi.mock("@/hooks/use-renderings", () => ({
  useRenderingTests: vi.fn(),
}));

vi.mock("@/hooks/use-mcp", () => ({
  useMCPStatus: vi.fn(),
  useMCPTools: vi.fn(),
  useMCPConnections: vi.fn(),
  useMCPApiKeys: vi.fn(),
  useToggleMCPTool: vi.fn(),
  useGenerateMCPApiKey: vi.fn(),
}));

vi.mock("@/hooks/use-design-sync", () => ({
  useDesignTokens: vi.fn(),
  useTokenDiff: vi
    .fn()
    .mockReturnValue({ data: undefined, error: undefined, isLoading: false, mutate: vi.fn() }),
}));

vi.mock("@/components/ui/empty-state", () => ({
  EmptyState: ({ title, description }: { title: string; description?: string }) => (
    <div data-testid="empty-state">
      <span>{title}</span>
      {description && <span>{description}</span>}
    </div>
  ),
}));

vi.mock("@/components/visual-qa/visual-qa-dialog", () => ({
  VisualQADialog: () => <div data-testid="visual-qa-dialog" />,
}));

vi.mock("@email-hub/ui/components/ui/skeleton", () => ({
  Skeleton: ({ className }: { className?: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: { children: React.ReactNode; href: string } & Record<string, unknown>) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Import hooks for mock control
import { useRenderingTests } from "@/hooks/use-renderings";
import {
  useMCPStatus,
  useMCPTools,
  useMCPConnections,
  useMCPApiKeys,
  useToggleMCPTool,
  useGenerateMCPApiKey,
} from "@/hooks/use-mcp";
import { useDesignTokens } from "@/hooks/use-design-sync";

// Import components under test
import { BrandColorEditor } from "../brand/brand-color-editor";
import { BrandTypographyEditor } from "../brand/brand-typography-editor";
import { ScoreOverviewCards } from "../intelligence/score-overview-cards";
import { RenderingSummaryCard } from "../intelligence/rendering-summary-card";
import { GraphCompletionResult } from "../knowledge/graph-completion-result";
import { MCPConfigPanel } from "../settings/MCPConfigPanel";
import { DesignTokensView } from "../design-sync/design-tokens-view";
import { VisualQAPanelTab } from "../visual-qa/visual-qa-panel-tab";

// Cast mocks for easy control
const mockUseRenderingTests = useRenderingTests as ReturnType<typeof vi.fn>;
const mockUseMCPStatus = useMCPStatus as ReturnType<typeof vi.fn>;
const mockUseMCPTools = useMCPTools as ReturnType<typeof vi.fn>;
const mockUseMCPConnections = useMCPConnections as ReturnType<typeof vi.fn>;
const mockUseMCPApiKeys = useMCPApiKeys as ReturnType<typeof vi.fn>;
const mockUseToggleMCPTool = useToggleMCPTool as ReturnType<typeof vi.fn>;
const mockUseGenerateMCPApiKey = useGenerateMCPApiKey as ReturnType<typeof vi.fn>;
const mockUseDesignTokens = useDesignTokens as ReturnType<typeof vi.fn>;

// ---------------------------------------------------------------------------
// 1. BrandColorEditor
// ---------------------------------------------------------------------------
describe("BrandColorEditor", () => {
  const colors = [
    { name: "Primary", hex: "#FF0000" },
    { name: "Secondary", hex: "#00FF00" },
  ];

  it("renders existing color swatches", () => {
    const onChange = vi.fn();
    render(<BrandColorEditor colors={colors} onChange={onChange} />);

    expect(screen.getByText("Brand Colors")).toBeInTheDocument();
    expect(screen.getByText("Primary")).toBeInTheDocument();
    expect(screen.getByText("#FF0000")).toBeInTheDocument();
    expect(screen.getByText("Secondary")).toBeInTheDocument();
    expect(screen.getByText("#00FF00")).toBeInTheDocument();
  });

  it("calls onChange when adding a color", () => {
    const onChange = vi.fn();
    render(<BrandColorEditor colors={colors} onChange={onChange} />);

    const nameInput = screen.getByPlaceholderText("Color name (e.g., Primary)");
    fireEvent.change(nameInput, { target: { value: "Accent" } });
    fireEvent.click(screen.getByText("Add"));

    expect(onChange).toHaveBeenCalledWith([...colors, { name: "Accent", hex: "#000000" }]);
  });

  it("calls onChange when removing a color", () => {
    const onChange = vi.fn();
    render(<BrandColorEditor colors={colors} onChange={onChange} />);

    // There should be two remove buttons (one per color)
    const removeButtons = screen
      .getAllByRole("button")
      .filter((btn) => !btn.textContent?.includes("Add"));
    fireEvent.click(removeButtons[0]!);

    expect(onChange).toHaveBeenCalledWith([colors[1]]);
  });

  it("hides add/remove controls when disabled", () => {
    render(<BrandColorEditor colors={colors} onChange={vi.fn()} disabled />);

    expect(screen.queryByText("Add")).not.toBeInTheDocument();
    expect(screen.getByText("Primary")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 2. BrandTypographyEditor
// ---------------------------------------------------------------------------
describe("BrandTypographyEditor", () => {
  const typography = [{ family: "Inter", weights: ["400", "600"], minSize: 12, maxSize: 48 }];

  it("renders font settings", () => {
    render(<BrandTypographyEditor typography={typography} onChange={vi.fn()} />);

    expect(screen.getByText("Typography")).toBeInTheDocument();
    expect(screen.getByText("Font Family")).toBeInTheDocument();
    expect(screen.getByText("Weights")).toBeInTheDocument();
    expect(screen.getByText("Min Size (px)")).toBeInTheDocument();
    expect(screen.getByText("Max Size (px)")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Inter")).toBeInTheDocument();
    expect(screen.getByDisplayValue("400, 600")).toBeInTheDocument();
  });

  it("calls onChange when font family is updated", () => {
    const onChange = vi.fn();
    render(<BrandTypographyEditor typography={typography} onChange={onChange} />);

    fireEvent.change(screen.getByDisplayValue("Inter"), {
      target: { value: "Roboto" },
    });

    expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ family: "Roboto" })]);
  });
});

// ---------------------------------------------------------------------------
// 3. ScoreOverviewCards
// ---------------------------------------------------------------------------
describe("ScoreOverviewCards", () => {
  const metrics: import("@/types/qa").QADashboardMetrics = {
    totalRuns: 42,
    avgScore: 0.87,
    passRate: 0.92,
    overrideCount: 3,
    checkAverages: [],
    scoreTrend: [],
  };

  it("renders all four score cards with correct values", () => {
    render(<ScoreOverviewCards metrics={metrics} />);

    expect(screen.getByText("Total QA Runs")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Average Score")).toBeInTheDocument();
    expect(screen.getByText("87%")).toBeInTheDocument();
    expect(screen.getByText("Pass Rate")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("Overrides")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows danger color for low pass rate", () => {
    const lowMetrics = { ...metrics, passRate: 0.5 };
    const { container } = render(<ScoreOverviewCards metrics={lowMetrics} />);

    // The pass rate value should have the danger class
    const passRateValue = screen.getByText("50%");
    expect(passRateValue.className).toContain("text-status-danger");
  });
});

// ---------------------------------------------------------------------------
// 4. RenderingSummaryCard
// ---------------------------------------------------------------------------
describe("RenderingSummaryCard", () => {
  beforeEach(() => {
    mockUseRenderingTests.mockReset();
  });

  it("shows skeleton when loading", () => {
    mockUseRenderingTests.mockReturnValue({ data: undefined, isLoading: true });
    render(<RenderingSummaryCard />);
    expect(screen.getByTestId("skeleton")).toBeInTheDocument();
  });

  it("shows empty state when no tests", () => {
    mockUseRenderingTests.mockReturnValue({
      data: { items: [] },
      isLoading: false,
    });
    render(<RenderingSummaryCard />);
    expect(screen.getByText("Email Client Rendering")).toBeInTheDocument();
    expect(screen.getByText("No Data")).toBeInTheDocument();
  });

  it("renders latest compatibility score", () => {
    mockUseRenderingTests.mockReturnValue({
      data: {
        items: [
          {
            clients_requested: 10,
            clients_completed: 8,
            screenshots: [
              { client_name: "Outlook", status: "failed" },
              { client_name: "Outlook", status: "completed" },
              { client_name: "Gmail", status: "completed" },
            ],
          },
        ],
      },
      isLoading: false,
    });
    render(<RenderingSummaryCard />);

    expect(screen.getByText("Email Client Rendering")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("View All")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 5. GraphCompletionResult
// ---------------------------------------------------------------------------
describe("GraphCompletionResult", () => {
  it("renders the query and answer content", () => {
    render(
      <GraphCompletionResult
        query="What is the best email client?"
        content="The best email client depends on your needs."
      />,
    );

    expect(screen.getByText("What is the best email client?")).toBeInTheDocument();
    expect(screen.getByText("The best email client depends on your needs.")).toBeInTheDocument();
    expect(screen.getByText("Answer from knowledge graph")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 6. MCPConfigPanel
// ---------------------------------------------------------------------------
describe("MCPConfigPanel", () => {
  beforeEach(() => {
    mockUseMCPStatus.mockReturnValue({
      data: { running: true, tool_count: 17 },
    });
    mockUseMCPTools.mockReturnValue({
      data: [
        { name: "qa_run", enabled: true, category: "qa", description: "Run QA checks" },
        {
          name: "render_email",
          enabled: false,
          category: "rendering",
          description: "Render email",
        },
      ],
      mutate: vi.fn(),
    });
    mockUseMCPConnections.mockReturnValue({
      data: [],
    });
    mockUseMCPApiKeys.mockReturnValue({
      data: [],
      mutate: vi.fn(),
    });
    mockUseToggleMCPTool.mockReturnValue({ trigger: vi.fn() });
    mockUseGenerateMCPApiKey.mockReturnValue({
      trigger: vi.fn(),
      isMutating: false,
    });
  });

  it("renders server status as running", () => {
    render(<MCPConfigPanel />);

    expect(screen.getByText("Server Status")).toBeInTheDocument();
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText(/17/)).toBeInTheDocument();
  });

  it("renders tool allowlist with categories", () => {
    render(<MCPConfigPanel />);

    expect(screen.getByText("Tool Allowlist")).toBeInTheDocument();
    expect(screen.getByText("qa")).toBeInTheDocument();
    expect(screen.getByText("rendering")).toBeInTheDocument();
    expect(screen.getByText("qa_run")).toBeInTheDocument();
    expect(screen.getByText("render_email")).toBeInTheDocument();
  });

  it("shows stopped status when not running", () => {
    mockUseMCPStatus.mockReturnValue({
      data: { running: false, tool_count: 0 },
    });
    render(<MCPConfigPanel />);

    expect(screen.getByText("Stopped")).toBeInTheDocument();
  });

  it("shows Generate Key button", () => {
    render(<MCPConfigPanel />);
    expect(screen.getByText("Generate Key")).toBeInTheDocument();
  });

  it("shows no connections message", () => {
    render(<MCPConfigPanel />);
    expect(screen.getByText("No recent connections")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 7. DesignTokensView
// ---------------------------------------------------------------------------
describe("DesignTokensView", () => {
  beforeEach(() => {
    mockUseDesignTokens.mockReset();
  });

  it("shows loader when loading", () => {
    mockUseDesignTokens.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: undefined,
    });
    const { container } = render(<DesignTokensView connectionId={1} />);
    // Loader2 renders an svg with animate-spin
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("shows error state with retry button", () => {
    mockUseDesignTokens.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("fail"),
    });
    render(<DesignTokensView connectionId={1} />);

    expect(screen.getByText("Failed to load design tokens")).toBeInTheDocument();
    expect(screen.getByText("Try again")).toBeInTheDocument();
  });

  it("shows empty state when no tokens", () => {
    mockUseDesignTokens.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: undefined,
    });
    render(<DesignTokensView connectionId={1} />);

    expect(screen.getByText("No design tokens")).toBeInTheDocument();
  });

  it("renders extracted colors and typography", () => {
    mockUseDesignTokens.mockReturnValue({
      data: {
        colors: [
          { name: "Brand Blue", hex: "#0066FF", opacity: 1 },
          { name: "Brand Red", hex: "#FF3333", opacity: 0.8 },
        ],
        typography: [{ name: "Heading", family: "Inter", weight: 700, size: 24, lineHeight: 32 }],
        spacing: [
          { name: "sm", value: 8 },
          { name: "md", value: 16 },
        ],
      },
      isLoading: false,
      error: undefined,
    });
    render(<DesignTokensView connectionId={1} />);

    // Colors
    expect(screen.getByText("Colors (2)")).toBeInTheDocument();
    expect(screen.getByText("Brand Blue")).toBeInTheDocument();
    expect(screen.getByText("#0066FF")).toBeInTheDocument();
    expect(screen.getByText("Brand Red")).toBeInTheDocument();

    // Typography
    expect(screen.getByText("Typography (1)")).toBeInTheDocument();
    expect(screen.getByText("Heading")).toBeInTheDocument();
    expect(screen.getByText("Inter · 700 · 24px / 32px")).toBeInTheDocument();

    // Spacing
    expect(screen.getByText("Spacing (2)")).toBeInTheDocument();
    expect(screen.getByText("sm")).toBeInTheDocument();
    expect(screen.getByText("8px")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 8. VisualQAPanelTab
// ---------------------------------------------------------------------------
describe("VisualQAPanelTab", () => {
  it("renders the Visual QA panel with button", () => {
    render(<VisualQAPanelTab html="<h1>Hello</h1>" entityType="component_version" entityId={1} />);

    expect(screen.getByText("Visual QA")).toBeInTheDocument();
    expect(screen.getByText("Compare screenshots across email clients")).toBeInTheDocument();
    expect(screen.getByText("View Visual QA")).toBeInTheDocument();
  });

  it("disables the button when html is empty", () => {
    render(<VisualQAPanelTab html="" entityType="component_version" entityId={1} />);

    const button = screen.getByRole("button", { name: /View Visual QA/i });
    expect(button).toBeDisabled();
  });

  it("opens dialog when button is clicked", () => {
    render(<VisualQAPanelTab html="<h1>Hello</h1>" entityType="component_version" entityId={1} />);

    fireEvent.click(screen.getByText("View Visual QA"));
    expect(screen.getByTestId("visual-qa-dialog")).toBeInTheDocument();
  });
});
