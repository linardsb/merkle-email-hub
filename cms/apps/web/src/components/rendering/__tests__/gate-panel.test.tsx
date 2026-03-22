import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("@/hooks/use-rendering-gate", () => ({
  useGateEvaluate: vi.fn(),
}));
vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

import { GatePanel } from "../gate-panel";
import { useGateEvaluate } from "@/hooks/use-rendering-gate";
import { useSession } from "next-auth/react";

const mockGateEvaluate = useGateEvaluate as ReturnType<typeof vi.fn>;
const mockUseSession = useSession as ReturnType<typeof vi.fn>;

function makeGateResult(overrides = {}) {
  return {
    passed: true,
    verdict: "pass" as const,
    mode: "enforce" as const,
    client_results: [
      {
        client_name: "gmail_web",
        confidence_score: 92,
        threshold: 85,
        passed: true,
        tier: "tier_1",
        blocking_reasons: [],
        remediation: [],
      },
      {
        client_name: "outlook_web",
        confidence_score: 88,
        threshold: 85,
        passed: true,
        tier: "tier_1",
        blocking_reasons: [],
        remediation: [],
      },
    ],
    blocking_clients: [],
    recommendations: [],
    evaluated_at: "2026-03-22T10:00:00Z",
    ...overrides,
  };
}

const defaultProps = {
  html: "<html>test</html>",
  projectId: 1,
  onApproved: vi.fn(),
  onCancel: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
  mockUseSession.mockReturnValue({ data: { user: { role: "admin" } } });
});

describe("GatePanel", () => {
  it("renders loading spinner during evaluation", () => {
    mockGateEvaluate.mockReturnValue({
      data: undefined,
      trigger: vi.fn(),
      isMutating: true,
      error: undefined,
    });

    render(<GatePanel {...defaultProps} />);
    expect(screen.getByText("Evaluating rendering confidence...")).toBeDefined();
  });

  it("shows error state with retry button", () => {
    const trigger = vi.fn();
    mockGateEvaluate.mockReturnValue({
      data: undefined,
      trigger,
      isMutating: false,
      error: new Error("Network error"),
    });

    render(<GatePanel {...defaultProps} />);
    expect(screen.getByText(/Gate evaluation failed/)).toBeDefined();

    fireEvent.click(screen.getByText("Retry"));
    expect(trigger).toHaveBeenCalled();
  });

  it("displays pass verdict with proceed button", () => {
    mockGateEvaluate.mockReturnValue({
      data: makeGateResult(),
      trigger: vi.fn(),
      isMutating: false,
      error: undefined,
    });

    render(<GatePanel {...defaultProps} approveLabel="Export" />);
    expect(screen.getByText("All Clients Pass")).toBeDefined();
    expect(screen.getByText("Export")).toBeDefined();
  });

  it("displays block verdict with override button for admin", () => {
    mockGateEvaluate.mockReturnValue({
      data: makeGateResult({
        passed: false,
        verdict: "block",
        blocking_clients: ["outlook_web"],
      }),
      trigger: vi.fn(),
      isMutating: false,
      error: undefined,
    });

    render(<GatePanel {...defaultProps} />);
    expect(screen.getByText(/Blocked/)).toBeDefined();
    expect(screen.getByText(/Override & Send Anyway/)).toBeDefined();
  });

  it("hides override button for non-admin when blocked", () => {
    mockUseSession.mockReturnValue({ data: { user: { role: "viewer" } } });
    mockGateEvaluate.mockReturnValue({
      data: makeGateResult({
        passed: false,
        verdict: "block",
        blocking_clients: ["outlook_web"],
      }),
      trigger: vi.fn(),
      isMutating: false,
      error: undefined,
    });

    render(<GatePanel {...defaultProps} />);
    expect(screen.queryByText(/Override & Send Anyway/)).toBeNull();
    expect(screen.getByText(/ask an admin/)).toBeDefined();
  });

  it("shows recommendations when present", () => {
    mockGateEvaluate.mockReturnValue({
      data: makeGateResult({
        recommendations: ["Consider adding dark mode styles"],
      }),
      trigger: vi.fn(),
      isMutating: false,
      error: undefined,
    });

    render(<GatePanel {...defaultProps} />);
    expect(screen.getByText("Consider adding dark mode styles")).toBeDefined();
  });

  it("renders client rows for each result", () => {
    mockGateEvaluate.mockReturnValue({
      data: makeGateResult(),
      trigger: vi.fn(),
      isMutating: false,
      error: undefined,
    });

    render(<GatePanel {...defaultProps} />);
    expect(screen.getByText("gmail_web")).toBeDefined();
    expect(screen.getByText("outlook_web")).toBeDefined();
  });

  it("calls onApproved when proceed button clicked", () => {
    const onApproved = vi.fn();
    mockGateEvaluate.mockReturnValue({
      data: makeGateResult(),
      trigger: vi.fn(),
      isMutating: false,
      error: undefined,
    });

    render(<GatePanel {...defaultProps} onApproved={onApproved} />);
    fireEvent.click(screen.getByText("Continue"));
    expect(onApproved).toHaveBeenCalledOnce();
  });
});
