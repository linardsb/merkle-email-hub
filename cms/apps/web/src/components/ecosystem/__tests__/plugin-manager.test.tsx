import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock hooks before component imports
vi.mock("@/hooks/use-plugins", () => ({
  usePlugins: vi.fn(),
  usePluginHealthSummary: vi.fn(),
  usePluginEnable: vi.fn(),
  usePluginDisable: vi.fn(),
  usePluginRestart: vi.fn(),
}));
vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

import { PluginManagerPanel } from "../PluginManagerPanel";
import { usePlugins, usePluginHealthSummary, usePluginEnable, usePluginDisable, usePluginRestart } from "@/hooks/use-plugins";
import { useSession } from "next-auth/react";

const mockPlugins = usePlugins as ReturnType<typeof vi.fn>;
const mockHealth = usePluginHealthSummary as ReturnType<typeof vi.fn>;
const mockEnable = usePluginEnable as ReturnType<typeof vi.fn>;
const mockDisable = usePluginDisable as ReturnType<typeof vi.fn>;
const mockRestart = usePluginRestart as ReturnType<typeof vi.fn>;
const mockSession = useSession as ReturnType<typeof vi.fn>;

function makePlugin(overrides = {}) {
  return {
    name: "qa-links",
    version: "1.0.0",
    plugin_type: "qa_check",
    permissions: ["read_templates"],
    status: "active" as const,
    loaded_at: "2026-01-01T00:00:00Z",
    error: null,
    description: "Validates email links",
    author: "Hub Team",
    tags: ["qa", "links"],
    ...overrides,
  };
}

function setupMocks({ plugins = [makePlugin()], isLoading = false, role = "admin" } = {}) {
  mockPlugins.mockReturnValue({
    data: { plugins, total: plugins.length },
    isLoading,
    mutate: vi.fn(),
  });
  mockHealth.mockReturnValue({
    data: {
      plugins: plugins.map((p) => ({ name: p.name, status: "healthy", message: null, latency_ms: 10 })),
      total: plugins.length,
      healthy: plugins.length,
      degraded: 0,
      unhealthy: 0,
    },
    isLoading: false,
  });
  mockEnable.mockReturnValue({ trigger: vi.fn(), isMutating: false });
  mockDisable.mockReturnValue({ trigger: vi.fn(), isMutating: false });
  mockRestart.mockReturnValue({ trigger: vi.fn(), isMutating: false });
  mockSession.mockReturnValue({ data: { user: { role } }, status: "authenticated" });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PluginManagerPanel", () => {
  it("renders plugin list", () => {
    setupMocks();
    render(<PluginManagerPanel />);

    expect(screen.getByText("qa-links")).toBeDefined();
  });

  it("shows health summary badges", () => {
    setupMocks({ plugins: [makePlugin(), makePlugin({ name: "brand-check" })] });
    render(<PluginManagerPanel />);

    expect(screen.getByText("2 healthy")).toBeDefined();
    expect(screen.getByText("0 degraded")).toBeDefined();
    expect(screen.getByText("0 unhealthy")).toBeDefined();
  });

  it("filters by status when Active tab clicked", () => {
    setupMocks({
      plugins: [
        makePlugin({ name: "active-plugin", status: "active" }),
        makePlugin({ name: "disabled-plugin", status: "disabled" }),
      ],
    });
    render(<PluginManagerPanel />);

    // Both visible initially
    expect(screen.getByText("active-plugin")).toBeDefined();
    expect(screen.getByText("disabled-plugin")).toBeDefined();

    // Click Active tab
    fireEvent.click(screen.getByText("Active"));

    // Only active visible
    expect(screen.getByText("active-plugin")).toBeDefined();
    expect(screen.queryByText("disabled-plugin")).toBeNull();
  });

  it("shows loading state", () => {
    setupMocks({ isLoading: true });
    const { container } = render(<PluginManagerPanel />);
    const pulseElements = container.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThan(0);
  });

  it("shows empty state for filter with no matches", () => {
    setupMocks({ plugins: [makePlugin({ status: "active" })] });
    render(<PluginManagerPanel />);

    // Click Disabled tab - no disabled plugins
    fireEvent.click(screen.getByText("Disabled"));
    expect(screen.getByText("No plugins match this filter.")).toBeDefined();
  });

  it("renders plugin type badge", () => {
    setupMocks();
    render(<PluginManagerPanel />);

    expect(screen.getByText("qa_check")).toBeDefined();
  });

  it("renders plugin version and author", () => {
    setupMocks();
    render(<PluginManagerPanel />);

    expect(screen.getByText("v1.0.0")).toBeDefined();
    expect(screen.getByText(/Hub Team/)).toBeDefined();
  });

  it("admin sees enable/disable toggle", () => {
    setupMocks({ role: "admin" });
    render(<PluginManagerPanel />);

    expect(screen.getByText("Disable")).toBeDefined();
  });

  it("non-admin does not see controls", () => {
    setupMocks({ role: "viewer" });
    render(<PluginManagerPanel />);

    expect(screen.queryByText("Disable")).toBeNull();
    expect(screen.queryByText("Enable")).toBeNull();
  });

  it("clicking disable calls usePluginDisable trigger", async () => {
    const disableTrigger = vi.fn();
    setupMocks({ role: "admin" });
    mockDisable.mockReturnValue({ trigger: disableTrigger, isMutating: false });

    render(<PluginManagerPanel />);
    fireEvent.click(screen.getByText("Disable"));

    expect(disableTrigger).toHaveBeenCalled();
  });

  it("shows empty state when no plugins", () => {
    setupMocks({ plugins: [] });
    render(<PluginManagerPanel />);

    expect(screen.getByText("No plugins match this filter.")).toBeDefined();
  });

  it("shows Refresh button", () => {
    setupMocks();
    render(<PluginManagerPanel />);

    expect(screen.getByText("Refresh")).toBeDefined();
  });
});
