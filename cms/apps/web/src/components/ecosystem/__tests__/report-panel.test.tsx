import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock hooks before component imports
vi.mock("@/hooks/use-reports", () => ({
  useGenerateQAReport: vi.fn(),
  useGenerateApprovalReport: vi.fn(),
  useGenerateRegressionReport: vi.fn(),
  useReportDownload: vi.fn(),
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

import { ReportPanel } from "../ReportPanel";
import {
  useGenerateQAReport,
  useGenerateApprovalReport,
  useGenerateRegressionReport,
  useReportDownload,
} from "@/hooks/use-reports";

const mockGenQA = useGenerateQAReport as ReturnType<typeof vi.fn>;
const mockGenApproval = useGenerateApprovalReport as ReturnType<typeof vi.fn>;
const mockGenRegression = useGenerateRegressionReport as ReturnType<typeof vi.fn>;
const mockDownload = useReportDownload as ReturnType<typeof vi.fn>;

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "sessionStorage", { value: sessionStorageMock });

function makeReport(overrides = {}) {
  return {
    report_id: "rpt-1",
    filename: "qa-report-2026.pdf",
    size_bytes: 45_000,
    generated_at: new Date().toISOString(),
    report_type: "qa" as const,
    ...overrides,
  };
}

function setupMocks() {
  mockGenQA.mockReturnValue({ trigger: vi.fn(), isMutating: false });
  mockGenApproval.mockReturnValue({ trigger: vi.fn(), isMutating: false });
  mockGenRegression.mockReturnValue({ trigger: vi.fn(), isMutating: false });
  mockDownload.mockReturnValue({ trigger: vi.fn() });
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorageMock.clear();
});

describe("ReportPanel", () => {
  it("renders empty state when no reports", () => {
    setupMocks();
    render(<ReportPanel />);

    expect(screen.getByText(/No reports yet/)).toBeDefined();
  });

  it("shows Generate Report button", () => {
    setupMocks();
    render(<ReportPanel />);

    expect(screen.getByText("Generate Report")).toBeDefined();
  });

  it("renders report history table from session storage", () => {
    const report = makeReport();
    sessionStorageMock.setItem("ecosystem-report-history", JSON.stringify([report]));

    setupMocks();
    render(<ReportPanel />);

    expect(screen.getByText("qa-report-2026.pdf")).toBeDefined();
    expect(screen.getByText("qa")).toBeDefined();
  });

  it("shows type badges with correct colors", () => {
    const reports = [
      makeReport({ report_id: "r1", report_type: "qa" }),
      makeReport({ report_id: "r2", report_type: "approval", filename: "approval.pdf" }),
      makeReport({ report_id: "r3", report_type: "regression", filename: "regression.pdf" }),
    ];
    sessionStorageMock.setItem("ecosystem-report-history", JSON.stringify(reports));

    setupMocks();
    render(<ReportPanel />);

    expect(screen.getByText("qa")).toBeDefined();
    expect(screen.getByText("approval")).toBeDefined();
    expect(screen.getByText("regression")).toBeDefined();
  });

  it("clicking generate opens dialog", () => {
    setupMocks();
    render(<ReportPanel />);

    fireEvent.click(screen.getByText("Generate Report"));
    expect(screen.getByTestId("dialog")).toBeDefined();
    expect(screen.getByText("Generate Report", { selector: "h2" })).toBeDefined();
  });

  it("generate dialog shows type selector with QA/Approval/Regression", () => {
    setupMocks();
    render(<ReportPanel />);

    fireEvent.click(screen.getByText("Generate Report"));

    // Type selector buttons in dialog
    const dialogEl = screen.getByTestId("dialog");
    expect(dialogEl.textContent).toContain("qa");
    expect(dialogEl.textContent).toContain("approval");
    expect(dialogEl.textContent).toContain("regression");
  });

  it("selecting QA shows QA-specific fields", () => {
    setupMocks();
    render(<ReportPanel />);

    fireEvent.click(screen.getByText("Generate Report"));

    // QA is default — should see QA Result ID and checkboxes
    expect(screen.getByText("QA Result ID")).toBeDefined();
    expect(screen.getByText("Include screenshots")).toBeDefined();
    expect(screen.getByText("Include chaos testing")).toBeDefined();
    expect(screen.getByText("Include deliverability")).toBeDefined();
  });

  it("selecting Regression shows regression-specific fields", () => {
    setupMocks();
    render(<ReportPanel />);

    fireEvent.click(screen.getByText("Generate Report"));

    // Click regression type
    const regressionBtn = screen.getAllByText("regression").find((el) => el.tagName === "BUTTON");
    if (regressionBtn) fireEvent.click(regressionBtn);

    expect(screen.getByText("Entity Type")).toBeDefined();
    expect(screen.getByText("Entity ID")).toBeDefined();
  });

  it("submitting QA report calls useGenerateQAReport", () => {
    const genFn = vi.fn().mockResolvedValue(makeReport());
    setupMocks();
    mockGenQA.mockReturnValue({ trigger: genFn, isMutating: false });

    render(<ReportPanel />);

    fireEvent.click(screen.getByText("Generate Report"));
    fireEvent.click(screen.getByText("Generate"));

    expect(genFn).toHaveBeenCalled();
  });

  it("renders table columns when reports exist", () => {
    sessionStorageMock.setItem("ecosystem-report-history", JSON.stringify([makeReport()]));
    setupMocks();
    render(<ReportPanel />);

    expect(screen.getByText("Type")).toBeDefined();
    expect(screen.getByText("Filename")).toBeDefined();
    expect(screen.getByText("Size")).toBeDefined();
    expect(screen.getByText("Generated")).toBeDefined();
    expect(screen.getByText("Actions")).toBeDefined();
  });
});
