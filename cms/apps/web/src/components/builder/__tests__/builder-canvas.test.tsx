import type { ReactNode } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { BuilderSection } from "@/types/visual-builder";
import { DEFAULT_RESPONSIVE, DEFAULT_ADVANCED } from "@/types/visual-builder";

// Mock @dnd-kit
vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useDraggable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
  }),
  useDroppable: () => ({ setNodeRef: vi.fn(), isOver: false }),
}));
vi.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  }),
  verticalListSortingStrategy: {},
}));
vi.mock("@dnd-kit/utilities", () => ({
  CSS: { Transform: { toString: () => null } },
}));

// Mock DOMPurify
vi.mock("dompurify", () => ({
  default: { sanitize: (html: string) => html },
}));

import { BuilderCanvas } from "../builder-canvas";

function makeSection(overrides: Partial<BuilderSection> = {}): BuilderSection {
  return {
    id: overrides.id ?? "sec-1",
    componentId: 1,
    componentName: overrides.componentName ?? "Hero Banner",
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

describe("BuilderCanvas", () => {
  const defaultProps = {
    sections: [] as BuilderSection[],
    selectedSectionId: null,
    onSelect: vi.fn(),
    onRemove: vi.fn(),
    onDuplicate: vi.fn(),
  };

  it("renders empty canvas with drag-here message", () => {
    render(<BuilderCanvas {...defaultProps} />);
    expect(screen.getByText("Drag components here to start building")).toBeInTheDocument();
  });

  it("renders sections in order", () => {
    const sections = [
      makeSection({ id: "s1", componentName: "Header" }),
      makeSection({ id: "s2", componentName: "Footer" }),
    ];
    render(<BuilderCanvas {...defaultProps} sections={sections} />);
    expect(screen.getByText("Header")).toBeInTheDocument();
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });

  it("selecting a section calls onSelect with section id", () => {
    const onSelect = vi.fn();
    const sections = [makeSection({ id: "s1" })];
    render(<BuilderCanvas {...defaultProps} sections={sections} onSelect={onSelect} />);
    const sectionEl = screen.getByRole("button", {
      name: /Section: Hero Banner/,
    });
    fireEvent.click(sectionEl);
    expect(onSelect).toHaveBeenCalledWith("s1");
  });

  it("clicking canvas background deselects", () => {
    const onSelect = vi.fn();
    const sections = [makeSection({ id: "s1" })];
    render(
      <BuilderCanvas
        {...defaultProps}
        sections={sections}
        selectedSectionId="s1"
        onSelect={onSelect}
      />,
    );
    // Click the outer container (presentation role)
    const canvas = screen.getByRole("presentation");
    fireEvent.click(canvas);
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("Escape key deselects", () => {
    const onSelect = vi.fn();
    const sections = [makeSection({ id: "s1" })];
    render(
      <BuilderCanvas
        {...defaultProps}
        sections={sections}
        selectedSectionId="s1"
        onSelect={onSelect}
      />,
    );
    const canvas = screen.getByRole("presentation");
    fireEvent.keyDown(canvas, { key: "Escape" });
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("selected section shows action toolbar with duplicate and delete", () => {
    const sections = [makeSection({ id: "s1" })];
    render(<BuilderCanvas {...defaultProps} sections={sections} selectedSectionId="s1" />);
    expect(screen.getByLabelText("Duplicate section")).toBeInTheDocument();
    expect(screen.getByLabelText("Remove section")).toBeInTheDocument();
    expect(screen.getByLabelText("Drag to reorder")).toBeInTheDocument();
  });

  it("unselected section hides action toolbar", () => {
    const sections = [makeSection({ id: "s1" })];
    render(<BuilderCanvas {...defaultProps} sections={sections} selectedSectionId={null} />);
    expect(screen.queryByLabelText("Duplicate section")).not.toBeInTheDocument();
  });

  it("duplicate button calls onDuplicate", () => {
    const onDuplicate = vi.fn();
    const sections = [makeSection({ id: "s1" })];
    render(
      <BuilderCanvas
        {...defaultProps}
        sections={sections}
        selectedSectionId="s1"
        onDuplicate={onDuplicate}
      />,
    );
    fireEvent.click(screen.getByLabelText("Duplicate section"));
    expect(onDuplicate).toHaveBeenCalledWith("s1");
  });

  it("delete button calls onRemove", () => {
    const onRemove = vi.fn();
    const sections = [makeSection({ id: "s1" })];
    render(
      <BuilderCanvas
        {...defaultProps}
        sections={sections}
        selectedSectionId="s1"
        onRemove={onRemove}
      />,
    );
    fireEvent.click(screen.getByLabelText("Remove section"));
    expect(onRemove).toHaveBeenCalledWith("s1");
  });

  it("section wrapper shows component name", () => {
    const sections = [makeSection({ componentName: "Custom Header" })];
    render(<BuilderCanvas {...defaultProps} sections={sections} />);
    expect(screen.getByText("Custom Header")).toBeInTheDocument();
  });

  it("multiple sections render in correct order", () => {
    const sections = [
      makeSection({ id: "s1", componentName: "First" }),
      makeSection({ id: "s2", componentName: "Second" }),
      makeSection({ id: "s3", componentName: "Third" }),
    ];
    render(<BuilderCanvas {...defaultProps} sections={sections} />);
    const names = screen.getAllByRole("button").map((el) => el.getAttribute("aria-label"));
    expect(names).toEqual(["Section: First", "Section: Second", "Section: Third"]);
  });

  it("section has aria-selected attribute", () => {
    const sections = [makeSection({ id: "s1" })];
    render(<BuilderCanvas {...defaultProps} sections={sections} selectedSectionId="s1" />);
    const section = screen.getByRole("button", {
      name: /Section: Hero Banner/,
    });
    expect(section).toHaveAttribute("aria-selected", "true");
  });

  it("Enter key on section calls onSelect", () => {
    const onSelect = vi.fn();
    const sections = [makeSection({ id: "s1" })];
    render(<BuilderCanvas {...defaultProps} sections={sections} onSelect={onSelect} />);
    const section = screen.getByRole("button", {
      name: /Section: Hero Banner/,
    });
    fireEvent.keyDown(section, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("s1");
  });

  it("section content renders HTML", () => {
    const sections = [makeSection({ html: "<div data-testid='content'>Email content</div>" })];
    render(<BuilderCanvas {...defaultProps} sections={sections} />);
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });

  it("no sections shows empty state, not section list", () => {
    render(<BuilderCanvas {...defaultProps} sections={[]} />);
    expect(screen.getByText("Drag components here to start building")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Section:/ })).not.toBeInTheDocument();
  });
});
