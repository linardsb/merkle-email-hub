import { describe, expect, it } from "vitest";
import { extractConfidence, stripConfidenceComment } from "./confidence";

describe("extractConfidence", () => {
  it("extracts valid confidence from HTML comment", () => {
    expect(extractConfidence("Hello <!-- CONFIDENCE: 0.85 --> world")).toBe(0.85);
  });

  it("extracts boundary values", () => {
    expect(extractConfidence("<!-- CONFIDENCE: 0 -->")).toBe(0);
    expect(extractConfidence("<!-- CONFIDENCE: 1 -->")).toBe(1);
    expect(extractConfidence("<!-- CONFIDENCE: 0.0 -->")).toBe(0);
    expect(extractConfidence("<!-- CONFIDENCE: 1.0 -->")).toBe(1);
  });

  it("returns null for missing comment", () => {
    expect(extractConfidence("plain text")).toBeNull();
    expect(extractConfidence("")).toBeNull();
  });

  it("returns null for out-of-range values", () => {
    expect(extractConfidence("<!-- CONFIDENCE: 1.5 -->")).toBeNull();
    expect(extractConfidence("<!-- CONFIDENCE: -0.1 -->")).toBeNull();
  });

  it("handles extra whitespace in comment", () => {
    expect(extractConfidence("<!--  CONFIDENCE:  0.72  -->")).toBe(0.72);
  });
});

describe("stripConfidenceComment", () => {
  it("removes confidence comment and trims", () => {
    expect(stripConfidenceComment("Hello <!-- CONFIDENCE: 0.85 --> world")).toBe("Hello  world");
  });

  it("returns trimmed content when no comment present", () => {
    expect(stripConfidenceComment("plain text")).toBe("plain text");
  });

  it("handles content that is only the comment", () => {
    expect(stripConfidenceComment("<!-- CONFIDENCE: 0.5 -->")).toBe("");
  });
});
