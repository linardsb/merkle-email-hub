// @ts-nocheck
/**
 * Integration tests verifying each migrated hook passes the correct POLL constant
 * to useSmartPolling and spreads the appropriate SWR_PRESETS.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

// ── Mock useSmartPolling to track what interval each hook passes ──
const mockUseSmartPolling = vi.fn((base: number) => base);
vi.mock("@/hooks/use-smart-polling", () => ({
  useSmartPolling: (...args: unknown[]) => mockUseSmartPolling(...args),
}));

// ── Standard SWR / fetcher mocks ──
vi.mock("@/lib/swr-fetcher", () => ({ fetcher: vi.fn() }));
vi.mock("@/lib/mutation-fetcher", () => ({
  mutationFetcher: vi.fn(),
  longMutationFetcher: vi.fn(),
}));
vi.mock("@/lib/auth-fetch", () => ({ authFetch: vi.fn() }));
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
const mockUseSWRMutation = vi
  .fn()
  .mockReturnValue({ trigger: vi.fn(), isMutating: false });
vi.mock("swr", () => ({ default: (...args: unknown[]) => mockUseSWR(...args) }));
vi.mock("swr/mutation", () => ({ default: (...args: unknown[]) => mockUseSWRMutation(...args) }));

beforeEach(() => {
  mockUseSWR.mockClear();
  mockUseSWRMutation.mockClear();
  mockUseSmartPolling.mockClear();
  mockUseSmartPolling.mockImplementation((base: number) => base);
});

// ── 1. useRenderingTestPolling ──

describe("useRenderingTestPolling — smart polling migration", () => {
  it("passes POLL.realtime (3000) to useSmartPolling", async () => {
    const { useRenderingTestPolling } = await import("../use-renderings");
    renderHook(() => useRenderingTestPolling(1));
    expect(mockUseSmartPolling).toHaveBeenCalledWith(3_000);
  });

  it("uses smart interval in conditional callback", async () => {
    mockUseSmartPolling.mockReturnValue(4_500); // simulate blurred state
    const { useRenderingTestPolling } = await import("../use-renderings");
    renderHook(() => useRenderingTestPolling(1));
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.refreshInterval({ status: "pending" })).toBe(4_500);
    expect(options.refreshInterval({ status: "completed" })).toBe(0);
  });

  it("spreads SWR_PRESETS.polling", async () => {
    const { useRenderingTestPolling } = await import("../use-renderings");
    renderHook(() => useRenderingTestPolling(1));
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.revalidateOnFocus).toBe(false);
    expect(options.dedupingInterval).toBe(5_000);
  });
});

// ── 2. useDesignImport ──

describe("useDesignImport — smart polling migration", () => {
  it("passes POLL.realtime (3000) when polling=true", async () => {
    const { useDesignImport } = await import("../use-design-sync");
    renderHook(() => useDesignImport(1, true));
    expect(mockUseSmartPolling).toHaveBeenCalledWith(3_000);
  });

  it("passes POLL.off (0) when polling=false", async () => {
    const { useDesignImport } = await import("../use-design-sync");
    renderHook(() => useDesignImport(1, false));
    expect(mockUseSmartPolling).toHaveBeenCalledWith(0);
  });

  it("spreads SWR_PRESETS.polling", async () => {
    const { useDesignImport } = await import("../use-design-sync");
    renderHook(() => useDesignImport(1, true));
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.revalidateOnFocus).toBe(false);
  });
});

// ── 3. useMCPStatus ──

describe("useMCPStatus — smart polling migration", () => {
  it("passes POLL.status (30000) to useSmartPolling", async () => {
    const { useMCPStatus } = await import("../use-mcp");
    renderHook(() => useMCPStatus());
    expect(mockUseSmartPolling).toHaveBeenCalledWith(30_000);
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.refreshInterval).toBe(30_000);
    expect(options.revalidateOnFocus).toBe(false);
  });
});

// ── 4. useMCPConnections ──

describe("useMCPConnections — smart polling migration", () => {
  it("passes POLL.moderate (15000) to useSmartPolling", async () => {
    const { useMCPConnections } = await import("../use-mcp");
    renderHook(() => useMCPConnections());
    expect(mockUseSmartPolling).toHaveBeenCalledWith(15_000);
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.refreshInterval).toBe(15_000);
    expect(options.revalidateOnFocus).toBe(false);
  });
});

// ── 5. useOntologySyncStatus ──

describe("useOntologySyncStatus — smart polling migration", () => {
  it("passes POLL.background (60000) to useSmartPolling", async () => {
    const { useOntologySyncStatus } = await import("../use-ontology");
    renderHook(() => useOntologySyncStatus());
    expect(mockUseSmartPolling).toHaveBeenCalledWith(60_000);
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.refreshInterval).toBe(60_000);
    expect(options.revalidateOnFocus).toBe(false);
  });
});

// ── 6. usePenpotConnections ──

describe("usePenpotConnections — smart polling migration", () => {
  it("passes POLL.background (60000) to useSmartPolling", async () => {
    const { usePenpotConnections } = await import("../use-penpot");
    renderHook(() => usePenpotConnections());
    expect(mockUseSmartPolling).toHaveBeenCalledWith(60_000);
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.refreshInterval).toBe(60_000);
    expect(options.revalidateOnFocus).toBe(false);
  });
});

// ── 7. usePlugins ──

describe("usePlugins — smart polling migration", () => {
  it("passes POLL.background (60000) to useSmartPolling", async () => {
    const { usePlugins } = await import("../use-plugins");
    renderHook(() => usePlugins());
    expect(mockUseSmartPolling).toHaveBeenCalledWith(60_000);
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.refreshInterval).toBe(60_000);
    expect(options.revalidateOnFocus).toBe(false);
  });
});

// ── 8. usePluginHealthSummary ──

describe("usePluginHealthSummary — smart polling migration", () => {
  it("passes POLL.background (60000) to useSmartPolling", async () => {
    const { usePluginHealthSummary } = await import("../use-plugins");
    renderHook(() => usePluginHealthSummary());
    expect(mockUseSmartPolling).toHaveBeenCalledWith(60_000);
    const options = mockUseSWR.mock.calls[0][2];
    expect(options.refreshInterval).toBe(60_000);
    expect(options.revalidateOnFocus).toBe(false);
  });
});
