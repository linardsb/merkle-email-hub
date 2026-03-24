// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// ── Mocks ──

const mockCreateApproval = vi.fn();
const mockTriggerPreCheck = vi.fn();

vi.mock("@/hooks/use-approvals", () => ({
  useCreateApproval: () => ({
    trigger: mockCreateApproval,
    isMutating: false,
  }),
}));

vi.mock("@/hooks/use-export-pre-check", () => ({
  useExportPreCheck: () => ({
    trigger: mockTriggerPreCheck,
    data: null,
  }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("lucide-react", () => {
  const makeIcon = (name: string) =>
    (props: Record<string, unknown>) => <svg data-testid={`icon-${name}`} {...props} />;
  return {
    Loader2: makeIcon("Loader2"),
    ShieldCheck: makeIcon("ShieldCheck"),
    CheckCircle2: makeIcon("CheckCircle2"),
    ShieldAlert: makeIcon("ShieldAlert"),
    Clock: makeIcon("Clock"),
  };
});

vi.mock("@email-hub/ui/components/ui/dialog", () => ({
  Dialog: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-content">{children}</div>
  ),
  DialogHeader: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogTitle: ({ children }: { children: React.ReactNode }) => (
    <h2>{children}</h2>
  ),
  DialogDescription: ({ children }: { children: React.ReactNode }) => (
    <p>{children}</p>
  ),
}));

vi.mock("../approval-status-badge", () => ({
  ApprovalStatusBadge: ({ status }: { status: string }) => (
    <span data-testid="approval-badge">{status}</span>
  ),
}));

import { ApprovalRequestDialog } from "../approval-request-dialog";
import { ApprovalGatePanel } from "../approval-gate-panel";
import { toast } from "sonner";
import type { ApprovalGateResult } from "@/types/approval";

beforeEach(() => {
  vi.clearAllMocks();
  mockCreateApproval.mockResolvedValue({ id: 1 });
  mockTriggerPreCheck.mockResolvedValue(null);
});

// ── ApprovalRequestDialog ──

describe("ApprovalRequestDialog", () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    buildId: 42,
    projectId: 1,
    compiledHtml: "<html></html>",
    onSubmitted: vi.fn(),
  };

  it("renders dialog with title and submit button", () => {
    render(<ApprovalRequestDialog {...defaultProps} />);
    expect(screen.getByRole("heading", { name: "Submit for Approval" })).toBeInTheDocument();
    expect(screen.getByText("Submit this build for review before export")).toBeInTheDocument();
    // Button with same text exists
    expect(
      screen.getAllByText("Submit for Approval").find((el) => el.tagName === "BUTTON"),
    ).toBeInTheDocument();
  });

  it("shows build ID", () => {
    render(<ApprovalRequestDialog {...defaultProps} />);
    expect(screen.getByText("#42")).toBeInTheDocument();
  });

  it("calls createApproval with correct payload on submit", async () => {
    render(<ApprovalRequestDialog {...defaultProps} />);
    const submitBtn = screen.getAllByText("Submit for Approval").find(
      (el) => el.tagName === "BUTTON",
    );
    fireEvent.click(submitBtn!);
    await vi.waitFor(() => {
      expect(mockCreateApproval).toHaveBeenCalledWith({
        build_id: 42,
        project_id: 1,
      });
    });
  });

  it("shows toast on success and calls onSubmitted", async () => {
    render(<ApprovalRequestDialog {...defaultProps} />);
    const submitBtn = screen.getAllByText("Submit for Approval").find(
      (el) => el.tagName === "BUTTON",
    );
    fireEvent.click(submitBtn!);
    await vi.waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Build submitted for approval");
      expect(defaultProps.onSubmitted).toHaveBeenCalled();
    });
  });

  it("shows toast.error on API failure", async () => {
    mockCreateApproval.mockRejectedValueOnce(new Error("Server error"));
    render(<ApprovalRequestDialog {...defaultProps} />);
    const submitBtn = screen.getAllByText("Submit for Approval").find(
      (el) => el.tagName === "BUTTON",
    );
    fireEvent.click(submitBtn!);
    await vi.waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Server error");
    });
  });

  it("shows error when no buildId", async () => {
    render(<ApprovalRequestDialog {...defaultProps} buildId={null} />);
    expect(screen.getByText("Not available")).toBeInTheDocument();
  });
});

// ── ApprovalGatePanel ──

describe("ApprovalGatePanel", () => {
  const onRequestApproval = vi.fn();

  it("returns null when required is false", () => {
    const result: ApprovalGateResult = {
      required: false,
      passed: false,
      reason: null,
      approval_id: null,
      approved_by: null,
      approved_at: null,
    };
    const { container } = render(
      <ApprovalGatePanel approvalResult={result} onRequestApproval={onRequestApproval} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("shows Approved with green checkmark when passed", () => {
    const result: ApprovalGateResult = {
      required: true,
      passed: true,
      reason: null,
      approval_id: 10,
      approved_by: "admin@test.com",
      approved_at: "2026-03-20T10:00:00Z",
    };
    render(
      <ApprovalGatePanel approvalResult={result} onRequestApproval={onRequestApproval} />,
    );
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.getByText(/admin@test\.com/)).toBeInTheDocument();
  });

  it("shows Approval Required with reason when not passed and no approval", () => {
    const result: ApprovalGateResult = {
      required: true,
      passed: false,
      reason: "Project requires approval before export",
      approval_id: null,
      approved_by: null,
      approved_at: null,
    };
    render(
      <ApprovalGatePanel approvalResult={result} onRequestApproval={onRequestApproval} />,
    );
    expect(screen.getByText("Approval Required")).toBeInTheDocument();
    expect(screen.getByText("Project requires approval before export")).toBeInTheDocument();
  });

  it("shows Submit for Approval link that calls onRequestApproval", () => {
    const result: ApprovalGateResult = {
      required: true,
      passed: false,
      reason: null,
      approval_id: null,
      approved_by: null,
      approved_at: null,
    };
    render(
      <ApprovalGatePanel approvalResult={result} onRequestApproval={onRequestApproval} />,
    );
    const link = screen.getByText("Submit for Approval");
    fireEvent.click(link);
    expect(onRequestApproval).toHaveBeenCalled();
  });

  it("shows pending review when approval exists but not passed", () => {
    const result: ApprovalGateResult = {
      required: true,
      passed: false,
      reason: "Awaiting reviewer",
      approval_id: 5,
      approved_by: null,
      approved_at: null,
    };
    render(
      <ApprovalGatePanel approvalResult={result} onRequestApproval={onRequestApproval} />,
    );
    expect(screen.getByText("Pending review")).toBeInTheDocument();
    expect(screen.getByTestId("approval-badge")).toBeInTheDocument();
  });
});
