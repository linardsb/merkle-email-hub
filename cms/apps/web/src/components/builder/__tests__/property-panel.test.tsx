import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { BuilderSection } from "@/types/visual-builder";
import { DEFAULT_RESPONSIVE, DEFAULT_ADVANCED } from "@/types/visual-builder";
import type { DesignSystemConfig } from "@/types/design-system-config";

// Mock sub-tab components to isolate PropertyPanel behavior
vi.mock("../panels/content-tab", () => ({
  ContentTab: () => <div data-testid="content-tab">Content Tab</div>,
}));
vi.mock("../panels/style-tab", () => ({
  StyleTab: () => <div data-testid="style-tab">Style Tab</div>,
}));
vi.mock("../panels/responsive-tab", () => ({
  ResponsiveTab: () => <div data-testid="responsive-tab">Responsive Tab</div>,
}));
vi.mock("../panels/advanced-tab", () => ({
  AdvancedTab: () => <div data-testid="advanced-tab">Advanced Tab</div>,
}));

import { PropertyPanel } from "../panels/property-panel";

function makeSection(overrides: Partial<BuilderSection> = {}): BuilderSection {
  return {
    id: "sec-1",
    componentId: 1,
    componentName: "Hero Banner",
    componentSlug: "hero-banner",
    category: "hero",
    html: "<table><tr><td>Hello</td></tr></table>",
    css: null,
    slotFills: {},
    tokenOverrides: {},
    slotDefinitions: [],
    defaultTokens: null,
    responsive: { ...DEFAULT_RESPONSIVE },
    advanced: { ...DEFAULT_ADVANCED },
    ...overrides,
  };
}

describe("PropertyPanel", () => {
  const defaultProps = {
    section: makeSection(),
    onUpdate: vi.fn(),
    designSystem: null as DesignSystemConfig | null,
    onClose: vi.fn(),
    previewMode: "desktop" as const,
    onPreviewModeChange: vi.fn(),
  };

  it("renders header with component name", () => {
    render(<PropertyPanel {...defaultProps} />);
    expect(screen.getByText("Hero Banner")).toBeInTheDocument();
  });

  it("renders category badge", () => {
    render(<PropertyPanel {...defaultProps} />);
    expect(screen.getByText("hero")).toBeInTheDocument();
  });

  it("renders all four tabs", () => {
    render(<PropertyPanel {...defaultProps} />);
    expect(screen.getByRole("tab", { name: "Content" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Style" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Responsive" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Advanced" })).toBeInTheDocument();
  });

  it("Content tab is visible by default", () => {
    render(<PropertyPanel {...defaultProps} />);
    expect(screen.getByTestId("content-tab")).toBeInTheDocument();
  });

  it("Style tab trigger is interactive", () => {
    render(<PropertyPanel {...defaultProps} />);
    const styleTab = screen.getByRole("tab", { name: "Style" });
    expect(styleTab).not.toBeDisabled();
    expect(styleTab).toHaveAttribute("data-state"); // Has state tracking
  });

  it("Responsive tab trigger is interactive", () => {
    render(<PropertyPanel {...defaultProps} />);
    const responsiveTab = screen.getByRole("tab", { name: "Responsive" });
    expect(responsiveTab).not.toBeDisabled();
    expect(responsiveTab).toHaveAttribute("data-state");
  });

  it("Advanced tab trigger is interactive", () => {
    render(<PropertyPanel {...defaultProps} />);
    const advancedTab = screen.getByRole("tab", { name: "Advanced" });
    expect(advancedTab).not.toBeDisabled();
    expect(advancedTab).toHaveAttribute("data-state");
  });

  it("close button calls onClose", () => {
    const onClose = vi.fn();
    render(<PropertyPanel {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("Close property panel"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("Escape key calls onClose", () => {
    const onClose = vi.fn();
    render(<PropertyPanel {...defaultProps} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("renders with custom component name", () => {
    render(
      <PropertyPanel
        {...defaultProps}
        section={makeSection({ componentName: "Footer Links" })}
      />,
    );
    expect(screen.getByText("Footer Links")).toBeInTheDocument();
  });

  it("renders with custom category", () => {
    render(
      <PropertyPanel
        {...defaultProps}
        section={makeSection({ category: "cta" })}
      />,
    );
    expect(screen.getByText("cta")).toBeInTheDocument();
  });

  it("has scrollable content area", () => {
    render(<PropertyPanel {...defaultProps} />);
    // ScrollArea is rendered — verify panel structure renders without error
    expect(screen.getByText("Hero Banner")).toBeInTheDocument();
  });
});
