import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSmartPolling } from "@/hooks/use-smart-polling";

describe("useSmartPolling", () => {
  let hiddenGetter: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    hiddenGetter = vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns baseInterval when tab is visible", () => {
    const { result } = renderHook(() => useSmartPolling(3000));
    expect(result.current).toBe(3000);
  });

  it("returns 0 when tab is hidden", () => {
    const { result } = renderHook(() => useSmartPolling(3000));

    act(() => {
      hiddenGetter.mockReturnValue(true);
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(result.current).toBe(0);
  });

  it("returns 1.5x interval when window is blurred but tab visible", () => {
    const { result } = renderHook(() => useSmartPolling(3000));

    act(() => {
      hiddenGetter.mockReturnValue(false);
      window.dispatchEvent(new Event("blur"));
    });

    expect(result.current).toBe(4500);
  });

  it("always returns 0 when baseInterval is 0", () => {
    const { result } = renderHook(() => useSmartPolling(0));

    expect(result.current).toBe(0);

    act(() => {
      hiddenGetter.mockReturnValue(false);
      window.dispatchEvent(new Event("blur"));
    });

    expect(result.current).toBe(0);

    act(() => {
      window.dispatchEvent(new Event("focus"));
    });

    expect(result.current).toBe(0);
  });

  it("cleans up event listeners on unmount", () => {
    const removeSpy = vi.spyOn(document, "removeEventListener");
    const removeWindowSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() => useSmartPolling(3000));
    unmount();

    const docEvents = removeSpy.mock.calls.map((c) => c[0]);
    const winEvents = removeWindowSpy.mock.calls.map((c) => c[0]);

    expect(docEvents).toContain("visibilitychange");
    expect(winEvents).toContain("focus");
    expect(winEvents).toContain("blur");

    removeSpy.mockRestore();
    removeWindowSpy.mockRestore();
  });

  it("resumes full speed on focus after blur", () => {
    const { result } = renderHook(() => useSmartPolling(5000));

    act(() => {
      window.dispatchEvent(new Event("blur"));
    });

    expect(result.current).toBe(7500);

    act(() => {
      window.dispatchEvent(new Event("focus"));
    });

    expect(result.current).toBe(5000);
  });
});
