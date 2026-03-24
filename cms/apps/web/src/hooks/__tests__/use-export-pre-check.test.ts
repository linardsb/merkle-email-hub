// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

const mockMutationFetcher = vi.fn();
const mockUseSWRMutation = vi.fn().mockReturnValue({
  trigger: vi.fn(),
  isMutating: false,
  data: undefined,
  error: undefined,
});

vi.mock("@/lib/mutation-fetcher", () => ({
  mutationFetcher: mockMutationFetcher,
}));

vi.mock("swr/mutation", () => ({
  default: (...args: unknown[]) => mockUseSWRMutation(...args),
}));

let useExportPreCheck: typeof import("@/hooks/use-export-pre-check").useExportPreCheck;

beforeEach(async () => {
  vi.clearAllMocks();
  const mod = await import("@/hooks/use-export-pre-check");
  useExportPreCheck = mod.useExportPreCheck;
});

describe("useExportPreCheck", () => {
  it("passes correct URL key", () => {
    renderHook(() => useExportPreCheck());
    expect(mockUseSWRMutation).toHaveBeenCalledWith(
      "/api/v1/connectors/export/pre-check",
      mockMutationFetcher,
    );
  });

  it("uses mutationFetcher", () => {
    renderHook(() => useExportPreCheck());
    const [, fetcher] = mockUseSWRMutation.mock.calls[0];
    expect(fetcher).toBe(mockMutationFetcher);
  });

  it("returns trigger and isMutating", () => {
    const { result } = renderHook(() => useExportPreCheck());
    expect(result.current).toHaveProperty("trigger");
    expect(result.current).toHaveProperty("isMutating");
  });
});
