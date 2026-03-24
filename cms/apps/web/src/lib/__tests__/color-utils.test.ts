import { describe, expect, it } from "vitest";
import { relativeLuminance, isDarkColor } from "../color-utils";

describe("relativeLuminance", () => {
  it("returns ~0 for black", () => {
    expect(relativeLuminance("#000000")).toBeCloseTo(0, 3);
  });

  it("returns ~1 for white", () => {
    expect(relativeLuminance("#ffffff")).toBeCloseTo(1, 3);
  });

  it("handles 3-digit hex", () => {
    expect(relativeLuminance("#fff")).toBeCloseTo(1, 3);
  });

  it("returns low luminance for dark gray", () => {
    expect(relativeLuminance("#101828")).toBeLessThan(0.05);
  });

  it("returns mid luminance for medium gray", () => {
    const lum = relativeLuminance("#808080");
    expect(lum).toBeGreaterThan(0.15);
    expect(lum).toBeLessThan(0.25);
  });
});

describe("isDarkColor", () => {
  it("dark colors return true", () => {
    expect(isDarkColor("#000000")).toBe(true);
    expect(isDarkColor("#101828")).toBe(true);
    expect(isDarkColor("#1a1a2e")).toBe(true);
  });

  it("light colors return false", () => {
    expect(isDarkColor("#ffffff")).toBe(false);
    expect(isDarkColor("#e5e5e5")).toBe(false);
    expect(isDarkColor("#93c5fd")).toBe(false);
  });
});
