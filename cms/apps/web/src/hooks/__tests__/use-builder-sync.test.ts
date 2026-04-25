import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { SectionNode } from "@/types/visual-builder";

vi.useFakeTimers();

describe("useBuilderSync", () => {
  const makeSections = (ids: string[]): SectionNode[] =>
    ids.map((id) => ({
      id,
      componentId: 0,
      componentName: id,
      slotValues: {},
      styleOverrides: {},
      htmlFragment: `<tr><td>${id}</td></tr>`,
    }));

  afterEach(() => {
    vi.clearAllTimers();
  });

  it("returns disabled state when not enabled", async () => {
    const { useBuilderSync } = await import("../use-builder-sync");
    const { result } = renderHook(() => useBuilderSync({ enabled: false }));
    expect(result.current.syncStatus).toBe("synced");
    expect(result.current.parsedSections).toEqual([]);
    expect(result.current.serializedHtml).toBeNull();
  });

  it("parses code changes into sections after 500ms debounce", async () => {
    const { useBuilderSync } = await import("../use-builder-sync");
    const { result } = renderHook(() => useBuilderSync({ enabled: true }));

    const html = `<html><body>
      <table><tbody>
        <tr data-section-id="s1"><td>Section 1</td></tr>
        <tr data-section-id="s2"><td>Section 2</td></tr>
      </tbody></table>
    </body></html>`;

    act(() => {
      result.current.handleCodeChange(html);
    });

    // Before debounce fires
    expect(result.current.syncStatus).toBe("syncing");
    expect(result.current.parsedSections).toEqual([]);

    // After 500ms debounce
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current.syncStatus).toBe("synced");
    expect(result.current.parsedSections.length).toBeGreaterThan(0);
  });

  it("serializes builder changes to HTML after 200ms debounce", async () => {
    const { useBuilderSync } = await import("../use-builder-sync");
    const { result } = renderHook(() => useBuilderSync({ enabled: true }));

    // Seed with initial HTML so template shell is available
    act(() => {
      result.current.handleCodeChange("<html><body><table><tbody></tbody></table></body></html>");
      vi.advanceTimersByTime(500);
    });

    const sections = makeSections(["hero", "footer"]);

    act(() => {
      result.current.handleBuilderChange(sections);
    });

    expect(result.current.syncStatus).toBe("syncing");

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(result.current.syncStatus).toBe("synced");
    expect(result.current.serializedHtml).not.toBeNull();
  });

  it("handles parse errors gracefully", async () => {
    const { useBuilderSync } = await import("../use-builder-sync");
    const { result } = renderHook(() => useBuilderSync({ enabled: true }));

    act(() => {
      result.current.handleCodeChange("not valid html at all {}[]");
      vi.advanceTimersByTime(500);
    });

    expect(result.current.syncStatus).toBe("parse_error");
    expect(result.current.parseError).toBeTruthy();

    // Dismiss clears error
    act(() => {
      result.current.dismissParseError();
    });

    expect(result.current.parseError).toBeNull();
    expect(result.current.syncStatus).toBe("synced");
  });

  it("disposes engine when disabled", async () => {
    const { useBuilderSync } = await import("../use-builder-sync");
    const { result, rerender } = renderHook(({ enabled }) => useBuilderSync({ enabled }), {
      initialProps: { enabled: true },
    });

    // Fully complete a sync cycle with parseable email HTML
    act(() => {
      result.current.handleCodeChange(
        `<html><body><table><tbody>
          <tr data-section-id="s1"><td>Hello</td></tr>
        </tbody></table></body></html>`,
      );
      vi.advanceTimersByTime(500);
    });
    expect(result.current.syncStatus).toBe("synced");

    // Now disable — engine is disposed, pending timers cleared
    rerender({ enabled: false });

    expect(result.current.syncStatus).toBe("synced");
  });

  it("builder wins when both change within debounce window", async () => {
    const { useBuilderSync } = await import("../use-builder-sync");
    const { result } = renderHook(() => useBuilderSync({ enabled: true }));

    // Seed template shell
    act(() => {
      result.current.handleCodeChange("<html><body><table><tbody></tbody></table></body></html>");
      vi.advanceTimersByTime(500);
    });

    // Code changes (500ms debounce starts)
    act(() => {
      result.current.handleCodeChange(
        "<html><body><table><tbody><tr><td>from code</td></tr></tbody></table></body></html>",
      );
    });

    // Builder changes within 500ms window (should cancel code sync)
    const sections = makeSections(["from-builder"]);
    act(() => {
      result.current.handleBuilderChange(sections);
    });

    // Advance past both debounce windows
    act(() => {
      vi.advanceTimersByTime(500);
    });

    // serializedHtml should reflect builder's sections
    expect(result.current.serializedHtml).not.toBeNull();
    // code→builder sync was canceled, so parsedSections still empty from seed
    expect(result.current.parsedSections).toEqual([]);
  });
});
