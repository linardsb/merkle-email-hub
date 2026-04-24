import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock hooks before component import
vi.mock("@/hooks/use-plugins", () => ({
  usePluginHealthSummary: vi.fn(),
}));
vi.mock("@/hooks/use-workflows", () => ({
  useWorkflows: vi.fn(),
}));
vi.mock("@/hooks/use-penpot", () => ({
  usePenpotConnections: vi.fn(),
}));
vi.mock("@/hooks/use-credentials-health", () => ({
  useCredentialHealth: vi.fn(),
}));

import { EcosystemDashboard } from "../EcosystemDashboard";
import { usePluginHealthSummary } from "@/hooks/use-plugins";
import { useWorkflows } from "@/hooks/use-workflows";
import { usePenpotConnections } from "@/hooks/use-penpot";
import { useCredentialHealth } from "@/hooks/use-credentials-health";

const mockHealthSummary = usePluginHealthSummary as ReturnType<typeof vi.fn>;
const mockWorkflows = useWorkflows as ReturnType<typeof vi.fn>;
const mockPenpot = usePenpotConnections as ReturnType<typeof vi.fn>;
const mockCredHealth = useCredentialHealth as ReturnType<typeof vi.fn>;

function makeHealthData(overrides = {}) {
  return {
    plugins: [
      { name: "qa-links", status: "healthy", message: null, latency_ms: 12 },
      { name: "brand-check", status: "degraded", message: "Slow", latency_ms: 350 },
    ],
    total: 2,
    healthy: 1,
    degraded: 1,
    unhealthy: 0,
    ...overrides,
  };
}

function makeWorkflowData(overrides = {}) {
  return {
    flows: [
      { id: "campaign-build", namespace: "hub", description: "Build campaign", is_template: false, revision: 1, has_schedule: true },
      { id: "qa-pipeline", namespace: "hub", description: "QA pipeline", is_template: true, revision: 2, has_schedule: false },
    ],
    ...overrides,
  };
}

function makePenpotData() {
  return [
    { id: 1, name: "Brand Kit", provider: "penpot", file_key: "abc", file_url: "", access_token_last4: "1234", status: "connected", last_synced_at: null, project_id: 1, project_name: "Marketing" },
  ];
}

function makeCredHealthData(overrides = {}) {
  return {
    services: [],
    total_keys: 0,
    healthy_total: 0,
    cooled_down_total: 0,
    unhealthy_total: 0,
    ...overrides,
  };
}

function setup(hookData = true) {
  if (hookData) {
    mockHealthSummary.mockReturnValue({ data: makeHealthData(), isLoading: false });
    mockWorkflows.mockReturnValue({ data: makeWorkflowData(), isLoading: false });
    mockPenpot.mockReturnValue({ data: makePenpotData(), isLoading: false });
    mockCredHealth.mockReturnValue({ data: makeCredHealthData(), isLoading: false });
  }
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("EcosystemDashboard", () => {
  it("renders 4 stat cards", () => {
    setup();
    render(<EcosystemDashboard onNavigate={vi.fn()} />);

    // Each label appears twice (stat card + quadrant), so use getAllByText
    expect(screen.getAllByText("Plugins").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Workflows").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Credentials").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Penpot").length).toBeGreaterThanOrEqual(2);
  });

  it("shows loading state when plugins loading", () => {
    mockHealthSummary.mockReturnValue({ data: undefined, isLoading: true });
    mockWorkflows.mockReturnValue({ data: makeWorkflowData(), isLoading: false });
    mockPenpot.mockReturnValue({ data: makePenpotData(), isLoading: false });
    mockCredHealth.mockReturnValue({ data: makeCredHealthData(), isLoading: false });

    const { container } = render(<EcosystemDashboard onNavigate={vi.fn()} />);
    const pulseElements = container.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThan(0);
  });

  it("shows loading state when workflows loading", () => {
    mockHealthSummary.mockReturnValue({ data: makeHealthData(), isLoading: false });
    mockWorkflows.mockReturnValue({ data: undefined, isLoading: true });
    mockPenpot.mockReturnValue({ data: makePenpotData(), isLoading: false });
    mockCredHealth.mockReturnValue({ data: makeCredHealthData(), isLoading: false });

    const { container } = render(<EcosystemDashboard onNavigate={vi.fn()} />);
    const pulseElements = container.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThan(0);
  });

  it("displays plugin health counts", () => {
    setup();
    render(<EcosystemDashboard onNavigate={vi.fn()} />);

    expect(screen.getByText("1 healthy")).toBeDefined();
    expect(screen.getByText("1 degraded")).toBeDefined();
    // "0 unhealthy" also appears in CredentialHealthCard; assert plugin quadrant contains it at least once
    expect(screen.getAllByText("0 unhealthy").length).toBeGreaterThanOrEqual(1);
  });

  it("displays workflow flow count", () => {
    setup();
    render(<EcosystemDashboard onNavigate={vi.fn()} />);

    expect(screen.getByText("2 flows")).toBeDefined();
  });

  it("displays penpot connection count", () => {
    setup();
    render(<EcosystemDashboard onNavigate={vi.fn()} />);

    expect(screen.getByText("1 connections")).toBeDefined();
  });

  it("displays plugin health stat card value", () => {
    setup();
    render(<EcosystemDashboard onNavigate={vi.fn()} />);

    expect(screen.getByText("1/2 healthy")).toBeDefined();
  });

  it("clicking View All on plugins quadrant calls onNavigate with plugins", () => {
    setup();
    const onNavigate = vi.fn();
    render(<EcosystemDashboard onNavigate={onNavigate} />);

    const viewAllButtons = screen.getAllByText(/View All/);
    fireEvent.click(viewAllButtons[0]!);
    expect(onNavigate).toHaveBeenCalledWith("plugins");
  });

  it("clicking View All on workflows quadrant calls onNavigate with workflows", () => {
    setup();
    const onNavigate = vi.fn();
    render(<EcosystemDashboard onNavigate={onNavigate} />);

    const viewAllButtons = screen.getAllByText(/View All/);
    fireEvent.click(viewAllButtons[1]!);
    expect(onNavigate).toHaveBeenCalledWith("workflows");
  });

  it("renders empty state when no penpot connections", () => {
    mockHealthSummary.mockReturnValue({ data: makeHealthData(), isLoading: false });
    mockWorkflows.mockReturnValue({ data: makeWorkflowData(), isLoading: false });
    mockPenpot.mockReturnValue({ data: [], isLoading: false });
    mockCredHealth.mockReturnValue({ data: makeCredHealthData(), isLoading: false });

    render(<EcosystemDashboard onNavigate={vi.fn()} />);
    expect(screen.getByText(/No Penpot connections yet/)).toBeDefined();
  });
});
