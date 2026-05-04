import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

// ── Mock useSmartPolling to track what interval the hook passes ──
const mockUseSmartPolling = vi.fn((base: number) => base);
vi.mock("@/hooks/use-smart-polling", () => ({
  useSmartPolling: (base: number) => mockUseSmartPolling(base),
}));

// ── Standard SWR / fetcher mocks ──
vi.mock("@/lib/swr-fetcher", () => ({ fetcher: vi.fn() }));
vi.mock("@/lib/api-error", () => ({
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      message: string,
      public code?: string,
    ) {
      super(message);
    }
  },
}));

const mockUseSWR = vi
  .fn()
  .mockReturnValue({ data: undefined, error: undefined, isLoading: true, mutate: vi.fn() });
vi.mock("swr", () => ({
  default: (key: unknown, fetcher: unknown, options?: unknown) => mockUseSWR(key, fetcher, options),
}));

beforeEach(() => {
  mockUseSWR.mockClear();
  mockUseSmartPolling.mockClear();
  mockUseSmartPolling.mockImplementation((base: number) => base);
});

describe("useProgress", () => {
  it("passes correct SWR key when operationId is set", async () => {
    const { useProgress } = await import("../use-progress");
    renderHook(() => useProgress("abc-123"));
    expect(mockUseSWR.mock.calls[0]![0]).toBe("/api/v1/progress/abc-123");
  });

  it("passes null key when operationId is null", async () => {
    const { useProgress } = await import("../use-progress");
    renderHook(() => useProgress(null));
    expect(mockUseSWR.mock.calls[0]![0]).toBeNull();
  });

  it("passes POLL.realtime (3000) to useSmartPolling", async () => {
    const { useProgress } = await import("../use-progress");
    renderHook(() => useProgress("abc-123"));
    expect(mockUseSmartPolling).toHaveBeenCalledWith(3_000);
  });

  it("uses smart interval for active operations, stops when completed", async () => {
    mockUseSmartPolling.mockReturnValue(4_500);
    const { useProgress } = await import("../use-progress");
    renderHook(() => useProgress("abc-123"));
    const options = mockUseSWR.mock.calls[0]![2];
    expect(options.refreshInterval({ status: "pending" })).toBe(4_500);
    expect(options.refreshInterval({ status: "processing" })).toBe(4_500);
    expect(options.refreshInterval({ status: "completed" })).toBe(0);
  });

  it("stops polling when operation has failed", async () => {
    const { useProgress } = await import("../use-progress");
    renderHook(() => useProgress("abc-123"));
    const options = mockUseSWR.mock.calls[0]![2];
    expect(options.refreshInterval({ status: "failed" })).toBe(0);
  });

  it("spreads SWR_PRESETS.polling options", async () => {
    const { useProgress } = await import("../use-progress");
    renderHook(() => useProgress("abc-123"));
    const options = mockUseSWR.mock.calls[0]![2];
    expect(options.revalidateOnFocus).toBe(false);
    expect(options.dedupingInterval).toBe(5_000);
  });
});
