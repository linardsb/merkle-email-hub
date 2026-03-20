// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";

// Mock dynamic imports — return simple components that expose props for inspection
vi.mock("next/dynamic", () => ({
  default: (importFn: () => Promise<unknown>) => {
    const importStr = importFn.toString();
    if (importStr.includes("code-editor")) {
      const Mock = (props: Record<string, unknown>) => (
        <div
          data-testid="code-editor"
          data-collaborative={props.collaborative !== undefined ? "true" : "false"}
        />
      );
      Mock.displayName = "MockCodeEditor";
      return Mock;
    }
    if (importStr.includes("visual-builder-panel")) {
      const Mock = (props: Record<string, unknown>) => (
        <div
          data-testid="visual-builder"
          data-has-synced-sections={Array.isArray(props.syncedSections) ? "true" : "false"}
          data-has-on-sections-change={typeof props.onSectionsChange === "function" ? "true" : "false"}
        />
      );
      Mock.displayName = "MockVisualBuilder";
      return Mock;
    }
    const Fallback = () => <div data-testid="dynamic-fallback" />;
    Fallback.displayName = "DynamicFallback";
    return Fallback;
  },
}));

const mockSyncCodeChange = vi.fn();
const mockSyncBuilderChange = vi.fn();
const mockDismissParseError = vi.fn();

vi.mock("@/hooks/use-builder-sync", () => ({
  useBuilderSync: vi.fn(() => ({
    syncStatus: "synced" as const,
    parseError: null,
    handleCodeChange: mockSyncCodeChange,
    handleBuilderChange: mockSyncBuilderChange,
    parsedSections: [],
    serializedHtml: null,
    dismissParseError: mockDismissParseError,
  })),
}));

// Mock view-switcher to avoid deep component tree
vi.mock("../../components/workspace/view-switcher", () => ({
  ViewSwitcher: () => <div data-testid="view-switcher" />,
}));

import { useBuilderSync } from "@/hooks/use-builder-sync";
import { EditorPanel } from "../workspace/editor-panel";

describe("EditorPanel sync wiring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== "undefined") {
      localStorage.clear();
    }
  });

  it("renders code editor view by default", () => {
    render(<EditorPanel value="<div>test</div>" onChange={vi.fn()} />);
    expect(screen.getByTestId("code-editor")).toBeTruthy();
  });

  it("passes collaborative prop in code-only mode", () => {
    const collabMock = {
      doc: {} as never,
      awareness: {} as never,
      user: { name: "Test", color: "#f00", role: "developer" },
    };

    render(
      <EditorPanel
        value="<div>test</div>"
        onChange={vi.fn()}
        collaborative={collabMock}
      />
    );

    const editor = screen.getByTestId("code-editor");
    expect(editor.dataset.collaborative).toBe("true");
  });

  it("renders split view with code editor and builder when tab is split", () => {
    localStorage.setItem("editor-view-1", "split");

    render(
      <EditorPanel
        value="<div>test</div>"
        onChange={vi.fn()}
        projectId={1}
      />
    );

    expect(screen.getByTestId("code-editor")).toBeTruthy();
    expect(screen.getByTestId("visual-builder")).toBeTruthy();
  });

  it("disables collaborative mode in split view", () => {
    localStorage.setItem("editor-view-2", "split");

    const collabMock = {
      doc: {} as never,
      awareness: {} as never,
      user: { name: "Test", color: "#f00", role: "developer" },
    };

    render(
      <EditorPanel
        value="<div>test</div>"
        onChange={vi.fn()}
        collaborative={collabMock}
        projectId={2}
      />
    );

    const editor = screen.getByTestId("code-editor");
    expect(editor.dataset.collaborative).toBe("false");
  });

  it("does not wire onSectionsChange in split mode (HTML path is higher fidelity)", () => {
    localStorage.setItem("editor-view-3", "split");

    render(
      <EditorPanel
        value="<div>test</div>"
        onChange={vi.fn()}
        projectId={3}
      />
    );

    const builder = screen.getByTestId("visual-builder");
    // Builder→code flows via useBuilderPreview HTML, not section-level sync
    expect(builder.dataset.hasOnSectionsChange).toBe("false");
  });

  it("passes syncedSections to builder in split mode", () => {
    localStorage.setItem("editor-view-4", "split");

    render(
      <EditorPanel
        value="<div>test</div>"
        onChange={vi.fn()}
        projectId={4}
      />
    );

    const builder = screen.getByTestId("visual-builder");
    expect(builder.dataset.hasSyncedSections).toBe("true");
  });

  it("seeds sync engine when entering split mode", () => {
    localStorage.setItem("editor-view-5", "split");

    render(
      <EditorPanel
        value="<html><body>seed</body></html>"
        onChange={vi.fn()}
        projectId={5}
      />
    );

    expect(mockSyncCodeChange).toHaveBeenCalledWith("<html><body>seed</body></html>");
  });

  it("shows parse error banner in split mode", () => {
    vi.mocked(useBuilderSync).mockReturnValue({
      syncStatus: "parse_error" as const,
      parseError: "HTML structure could not be parsed",
      handleCodeChange: mockSyncCodeChange,
      handleBuilderChange: mockSyncBuilderChange,
      parsedSections: [],
      serializedHtml: null,
      dismissParseError: mockDismissParseError,
    });

    localStorage.setItem("editor-view-6", "split");

    render(
      <EditorPanel
        value="<div>bad</div>"
        onChange={vi.fn()}
        projectId={6}
      />
    );

    expect(screen.getByText("HTML structure could not be parsed")).toBeTruthy();
    expect(screen.getByText("Dismiss")).toBeTruthy();
  });
});
