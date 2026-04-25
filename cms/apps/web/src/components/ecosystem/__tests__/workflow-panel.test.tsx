import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock hooks before component imports
vi.mock("@/hooks/use-workflows", () => ({
  useWorkflows: vi.fn(),
  useWorkflowStatus: vi.fn(),
  useWorkflowLogs: vi.fn(),
  useTriggerWorkflow: vi.fn(),
}));

// Mock Dialog components
vi.mock("@email-hub/ui/components/ui/dialog", () => ({
  Dialog: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
}));

import { WorkflowPanel } from "../WorkflowPanel";
import {
  useWorkflows,
  useWorkflowStatus,
  useWorkflowLogs,
  useTriggerWorkflow,
} from "@/hooks/use-workflows";

const mockWorkflows = useWorkflows as ReturnType<typeof vi.fn>;
const mockWorkflowStatus = useWorkflowStatus as ReturnType<typeof vi.fn>;
const mockWorkflowLogs = useWorkflowLogs as ReturnType<typeof vi.fn>;
const mockTrigger = useTriggerWorkflow as ReturnType<typeof vi.fn>;

function makeFlow(overrides = {}) {
  return {
    id: "campaign-build",
    namespace: "hub",
    description: "Build and send campaign",
    is_template: false,
    revision: 1,
    has_schedule: false,
    ...overrides,
  };
}

function setupMocks({ flows = [makeFlow()], isLoading = false } = {}) {
  mockWorkflows.mockReturnValue({
    data: { flows },
    isLoading,
  });
  mockWorkflowStatus.mockReturnValue({ data: undefined });
  mockWorkflowLogs.mockReturnValue({ data: undefined });
  mockTrigger.mockReturnValue({ trigger: vi.fn(), isMutating: false });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("WorkflowPanel", () => {
  it("renders available flows", () => {
    setupMocks();
    render(<WorkflowPanel />);

    expect(screen.getByText("campaign-build")).toBeDefined();
    expect(screen.getByText("Build and send campaign")).toBeDefined();
  });

  it("shows template badge on template flows", () => {
    setupMocks({ flows: [makeFlow({ is_template: true })] });
    render(<WorkflowPanel />);

    expect(screen.getByText("Template")).toBeDefined();
  });

  it("shows scheduled badge on scheduled flows", () => {
    setupMocks({ flows: [makeFlow({ has_schedule: true })] });
    render(<WorkflowPanel />);

    expect(screen.getByText("Scheduled")).toBeDefined();
  });

  it("shows loading state", () => {
    setupMocks({ isLoading: true });
    const { container } = render(<WorkflowPanel />);
    const pulseElements = container.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThan(0);
  });

  it("shows empty state when no flows", () => {
    setupMocks({ flows: [] });
    render(<WorkflowPanel />);

    // No flow cards rendered — the flows grid should be empty
    expect(screen.queryByText("campaign-build")).toBeNull();
  });

  it("clicking trigger opens dialog", () => {
    setupMocks();
    render(<WorkflowPanel />);

    fireEvent.click(screen.getByText("Trigger"));
    expect(screen.getByTestId("dialog")).toBeDefined();
    expect(screen.getByText("Trigger Workflow")).toBeDefined();
  });

  it("trigger dialog has flow selector", () => {
    setupMocks({ flows: [makeFlow(), makeFlow({ id: "qa-pipeline" })] });
    render(<WorkflowPanel />);

    fireEvent.click(screen.getAllByText("Trigger")[0]!);

    const select = screen.getByRole("combobox");
    expect(select).toBeDefined();
  });

  it("trigger dialog validates JSON inputs", () => {
    setupMocks();
    render(<WorkflowPanel />);

    fireEvent.click(screen.getByText("Trigger"));

    // Type invalid JSON
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "{invalid" } });

    // Click the trigger button in dialog (the second "Trigger" text)
    const triggerButtons = screen.getAllByText("Trigger");
    fireEvent.click(triggerButtons[triggerButtons.length - 1]!);

    expect(screen.getByText("Invalid JSON")).toBeDefined();
  });

  it("trigger dialog submits correctly", async () => {
    const triggerFn = vi.fn().mockResolvedValue({
      execution_id: "exec-1",
      flow_id: "campaign-build",
      status: "CREATED",
      started: "2026-01-01T00:00:00Z",
      ended: null,
      inputs: {},
      outputs: {},
      task_runs: [],
    });
    setupMocks();
    mockTrigger.mockReturnValue({ trigger: triggerFn, isMutating: false });

    render(<WorkflowPanel />);

    fireEvent.click(screen.getByText("Trigger"));

    const triggerButtons = screen.getAllByText("Trigger");
    fireEvent.click(triggerButtons[triggerButtons.length - 1]!);

    expect(triggerFn).toHaveBeenCalledWith({
      flow_id: "campaign-build",
      inputs: {},
    });
  });

  it("renders Available Flows heading", () => {
    setupMocks();
    render(<WorkflowPanel />);

    expect(screen.getByText("Available Flows")).toBeDefined();
  });

  it("shows multiple flows", () => {
    setupMocks({
      flows: [
        makeFlow({ id: "flow-1", description: "First flow" }),
        makeFlow({ id: "flow-2", description: "Second flow" }),
        makeFlow({ id: "flow-3", description: "Third flow" }),
      ],
    });
    render(<WorkflowPanel />);

    expect(screen.getByText("flow-1")).toBeDefined();
    expect(screen.getByText("flow-2")).toBeDefined();
    expect(screen.getByText("flow-3")).toBeDefined();
  });
});
