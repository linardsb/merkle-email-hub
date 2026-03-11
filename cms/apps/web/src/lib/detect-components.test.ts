import { describe, expect, it } from "vitest";
import { detectComponentRefs } from "./detect-components";

describe("detectComponentRefs", () => {
  it("returns empty array for plain HTML", () => {
    expect(detectComponentRefs("<div>Hello</div>")).toEqual([]);
  });

  it("returns empty array for empty string", () => {
    expect(detectComponentRefs("")).toEqual([]);
  });

  it("detects component with bare slug", () => {
    expect(
      detectComponentRefs('<component src="header-v2">')
    ).toEqual(["header-v2"]);
  });

  it("detects component with components/ prefix", () => {
    expect(
      detectComponentRefs('<component src="components/cta-primary">')
    ).toEqual(["cta-primary"]);
  });

  it("detects multiple components", () => {
    const html = `
      <component src="header-v2">
      <div>content</div>
      <component src="components/cta-primary">
      <component src="hero-banner">
    `;
    expect(detectComponentRefs(html)).toEqual([
      "header-v2",
      "cta-primary",
      "hero-banner",
    ]);
  });

  it("deduplicates repeated components", () => {
    const html = `
      <component src="header-v2">
      <component src="header-v2">
    `;
    expect(detectComponentRefs(html)).toEqual(["header-v2"]);
  });

  it("handles single quotes", () => {
    expect(
      detectComponentRefs("<component src='footer-v1'>")
    ).toEqual(["footer-v1"]);
  });

  it("handles extra attributes", () => {
    expect(
      detectComponentRefs('<component class="block" src="sidebar" data-v="1">')
    ).toEqual(["sidebar"]);
  });

  it("is case insensitive for tag name", () => {
    expect(
      detectComponentRefs('<Component src="my-comp">')
    ).toEqual(["my-comp"]);
  });
});
