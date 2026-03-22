import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("@/hooks/use-rendering-dashboard", () => ({
  useScreenshotsWithConfidence: vi.fn(),
  useCalibrationSummary: vi.fn(),
  useTriggerCalibration: vi.fn(),
}));
vi.mock("@/hooks/use-rendering-gate", () => ({
  useGateEvaluate: vi.fn(),
}));
vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

import { RenderingDashboard } from "../rendering-dashboard";
import {
  useScreenshotsWithConfidence,
  useCalibrationSummary,
  useTriggerCalibration,
} from "@/hooks/use-rendering-dashboard";
import { useGateEvaluate } from "@/hooks/use-rendering-gate";
import { useSession } from "next-auth/react";

const mockScreenshots = useScreenshotsWithConfidence as ReturnType<typeof vi.fn>;
const mockCalibration = useCalibrationSummary as ReturnType<typeof vi.fn>;
const mockTriggerCalibration = useTriggerCalibration as ReturnType<typeof vi.fn>;
const mockGateEvaluate = useGateEvaluate as ReturnType<typeof vi.fn>;
const mockUseSession = useSession as ReturnType<typeof vi.fn>;

function makeScreenshotData() {
  return {
    screenshots: [
      { client_name: "gmail_web", image_base64: "abc123", viewport: "1280x1024", browser: "chrome" },
      { client_name: "outlook_web", image_base64: "def456", viewport: "1280x1024", browser: "chrome" },
    ],
    clients_rendered: 2,
    clients_failed: 0,
  };
}

function makeGateResult() {
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
        confidence_score: 78,
        threshold: 70,
        passed: true,
        tier: "tier_2",
        blocking_reasons: [],
        remediation: [],
      },
    ],
    blocking_clients: [],
    recommendations: [],
    evaluated_at: "2026-03-22T10:00:00Z",
  };
}

function makeCalibrationSummary() {
  return {
    items: [
      {
        client_id: "gmail_web",
        current_accuracy: 94,
        sample_count: 50,
        last_calibrated: "2026-03-20T10:00:00Z",
        accuracy_trend: [88, 90, 91, 92, 93, 94],
        regression_alert: false,
      },
    ],
  };
}

function setupMocks(overrides: {
  screenshots?: ReturnType<typeof makeScreenshotData> | undefined;
  gateResult?: ReturnType<typeof makeGateResult> | undefined;
  screenshotsLoading?: boolean;
  gateLoading?: boolean;
  role?: string;
} = {}) {
  const screenshotsTrigger = vi.fn();
  const gateTrigger = vi.fn();

  mockScreenshots.mockReturnValue({
    data: overrides.screenshots,
    trigger: screenshotsTrigger,
    isMutating: overrides.screenshotsLoading ?? false,
    error: undefined,
  });
  mockGateEvaluate.mockReturnValue({
    data: overrides.gateResult,
    trigger: gateTrigger,
    isMutating: overrides.gateLoading ?? false,
    error: undefined,
  });
  mockCalibration.mockReturnValue({
    data: makeCalibrationSummary(),
    isLoading: false,
  });
  mockTriggerCalibration.mockReturnValue({
    trigger: vi.fn(),
  });
  mockUseSession.mockReturnValue({
    data: { user: { role: overrides.role ?? "admin" } },
  });

  return { screenshotsTrigger, gateTrigger };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RenderingDashboard", () => {
  it("shows empty state when html is null", () => {
    setupMocks();
    render(<RenderingDashboard html={null} projectId={null} />);
    expect(screen.getByText("No email to preview")).toBeDefined();
  });

  it("shows generate button when html is provided but no data", () => {
    setupMocks();
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);
    expect(screen.getByText("Generate Rendering Previews")).toBeDefined();
  });

  it("triggers screenshots and gate on generate click", () => {
    const { screenshotsTrigger, gateTrigger } = setupMocks();
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);

    fireEvent.click(screen.getByText("Generate Rendering Previews"));
    expect(screenshotsTrigger).toHaveBeenCalledWith({ html: "<html>test</html>" });
    expect(gateTrigger).toHaveBeenCalledWith({
      html: "<html>test</html>",
      project_id: 1,
    });
  });

  it("shows loading state during data fetch", () => {
    setupMocks({ screenshotsLoading: true });
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);
    expect(screen.getByText("Generating rendering previews...")).toBeDefined();
  });

  it("renders preview grid with correct number of cards", () => {
    setupMocks({
      screenshots: makeScreenshotData(),
      gateResult: makeGateResult(),
    });
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);

    // Both gmail_web and outlook_web are base clients (not dark variants)
    const images = screen.getAllByRole("img");
    expect(images.length).toBe(2);
  });

  it("renders confidence summary bar", () => {
    setupMocks({
      screenshots: makeScreenshotData(),
      gateResult: makeGateResult(),
    });
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);

    expect(screen.getByText(/Overall rendering confidence/)).toBeDefined();
  });

  it("shows gate status section", () => {
    setupMocks({
      screenshots: makeScreenshotData(),
      gateResult: makeGateResult(),
    });
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);

    expect(screen.getByText("Rendering Gate")).toBeDefined();
    expect(screen.getByText("All Clients Pass")).toBeDefined();
  });

  it("shows calibration panel only for admin", () => {
    setupMocks({
      screenshots: makeScreenshotData(),
      gateResult: makeGateResult(),
      role: "admin",
    });
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);

    expect(screen.getByText("Calibration Health")).toBeDefined();
  });

  it("hides calibration panel for non-admin", () => {
    setupMocks({
      screenshots: makeScreenshotData(),
      gateResult: makeGateResult(),
      role: "viewer",
    });
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);

    expect(screen.queryByText("Calibration Health")).toBeNull();
  });

  it("shows client names from gate results", () => {
    setupMocks({
      screenshots: makeScreenshotData(),
      gateResult: makeGateResult(),
    });
    render(<RenderingDashboard html="<html>test</html>" projectId={1} />);

    // Client names appear in both preview cards and gate rows
    expect(screen.getAllByText("gmail_web").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("outlook_web").length).toBeGreaterThanOrEqual(1);
  });
});
