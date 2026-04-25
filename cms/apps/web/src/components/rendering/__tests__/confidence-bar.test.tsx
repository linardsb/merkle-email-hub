import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { ConfidenceBar } from "../confidence-bar";

describe("ConfidenceBar", () => {
  it("renders green bar when score > 85", () => {
    const { container } = render(<ConfidenceBar score={90} />);
    const fill = container.querySelector(".bg-status-success");
    expect(fill).toBeDefined();
    expect(fill).not.toBeNull();
  });

  it("renders yellow bar when score 60-85", () => {
    const { container } = render(<ConfidenceBar score={72} />);
    const fill = container.querySelector(".bg-status-warning");
    expect(fill).toBeDefined();
    expect(fill).not.toBeNull();
  });

  it("renders red bar when score < 60", () => {
    const { container } = render(<ConfidenceBar score={45} />);
    const fill = container.querySelector(".bg-status-danger");
    expect(fill).toBeDefined();
    expect(fill).not.toBeNull();
  });

  it("renders threshold marker at correct position", () => {
    const { container } = render(<ConfidenceBar score={80} threshold={70} />);
    const marker = container.querySelector("[title='Threshold: 70%']");
    expect(marker).toBeDefined();
    expect(marker).not.toBeNull();
  });

  it("does not render threshold marker when not provided", () => {
    const { container } = render(<ConfidenceBar score={80} />);
    const markers = container.querySelectorAll(".w-0\\.5.bg-foreground-muted");
    expect(markers.length).toBe(0);
  });

  it("clamps score to 0-100 range", () => {
    const { container: overContainer } = render(<ConfidenceBar score={150} />);
    const overFill = overContainer.querySelector(".bg-status-success");
    expect(overFill).not.toBeNull();
    expect((overFill as HTMLElement).style.width).toBe("100%");

    const { container: underContainer } = render(<ConfidenceBar score={-10} />);
    const underFill = underContainer.querySelector(".bg-status-danger");
    expect(underFill).not.toBeNull();
    expect((underFill as HTMLElement).style.width).toBe("0%");
  });

  it("renders with sm size by default", () => {
    const { container } = render(<ConfidenceBar score={80} />);
    const track = container.querySelector(".h-2.rounded-full.bg-surface-muted");
    expect(track).not.toBeNull();
  });

  it("renders with md size when specified", () => {
    const { container } = render(<ConfidenceBar score={80} size="md" />);
    const track = container.querySelector(".h-3.rounded-full.bg-surface-muted");
    expect(track).not.toBeNull();
  });

  it("shows breakdown in tooltip when provided", () => {
    const breakdown = {
      emulator_coverage: 0.85,
      css_compatibility: 0.92,
      calibration_accuracy: 0.78,
      layout_complexity: 0.65,
      known_blind_spots: [],
    };
    const { container } = render(<ConfidenceBar score={80} breakdown={breakdown} />);
    const wrapper = container.querySelector("[title]");
    expect(wrapper).not.toBeNull();
    const title = (wrapper as HTMLElement).getAttribute("title");
    expect(title).toContain("Emulator coverage: 85%");
    expect(title).toContain("CSS compatibility: 92%");
  });
});
