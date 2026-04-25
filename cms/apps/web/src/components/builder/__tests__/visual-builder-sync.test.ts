import { describe, it, expect } from "vitest";
import type { SectionNode } from "@/types/visual-builder";
import { DEFAULT_RESPONSIVE, DEFAULT_ADVANCED } from "@/types/visual-builder";
import type { AppComponentsSchemasVersionResponse as VersionResponse } from "@email-hub/sdk";
import { inferSlotDefinitions, sectionNodeToBuilderSection } from "../visual-builder-panel";

function makeSectionNode(overrides: Partial<SectionNode> = {}): SectionNode {
  return {
    id: "sec-1",
    componentId: 0,
    componentName: "Unknown",
    slotValues: {},
    styleOverrides: {},
    htmlFragment: "<table><tr><td>Hello</td></tr></table>",
    ...overrides,
  };
}

describe("inferSlotDefinitions", () => {
  it("extracts slot definitions from data-slot-name elements", () => {
    const html = `
      <table>
        <tr><td>
          <h2 data-slot-name="headline">Default headline</h2>
          <p data-slot-name="body_text">Body content goes here.</p>
          <a data-slot-name="cta_link" href="#">Click me</a>
        </td></tr>
      </table>
    `;
    const defs = inferSlotDefinitions(html);
    expect(defs).toHaveLength(3);

    expect(defs[0]).toMatchObject({
      slot_id: "headline",
      slot_type: "headline",
      selector: '[data-slot-name="headline"]',
    });
    expect(defs[1]).toMatchObject({
      slot_id: "body_text",
      slot_type: "body",
      selector: '[data-slot-name="body_text"]',
    });
    expect(defs[2]).toMatchObject({
      slot_id: "cta_link",
      slot_type: "cta",
      selector: '[data-slot-name="cta_link"]',
    });
  });

  it("detects image slots from <img> elements", () => {
    const html = '<img data-slot-name="hero_image" src="x.png">';
    const defs = inferSlotDefinitions(html);
    expect(defs).toHaveLength(1);
    expect(defs[0]).toMatchObject({ slot_type: "image" });
  });

  it("deduplicates repeated slot names", () => {
    const html = `
      <p data-slot-name="body">A</p>
      <p data-slot-name="body">B</p>
    `;
    const defs = inferSlotDefinitions(html);
    expect(defs).toHaveLength(1);
  });

  it("returns empty array for HTML without slots", () => {
    const defs = inferSlotDefinitions("<table><tr><td>No slots</td></tr></table>");
    expect(defs).toHaveLength(0);
  });
});

describe("sectionNodeToBuilderSection", () => {
  it("uses inferred slot definitions when no cache is provided", () => {
    const node = makeSectionNode({
      htmlFragment: '<table><tr><td><h1 data-slot-name="title">Hello</h1></td></tr></table>',
    });
    const result = sectionNodeToBuilderSection(node);

    expect(result.slotDefinitions).toHaveLength(1);
    expect(result.slotDefinitions[0]?.slot_id).toBe("title");
    expect(result.defaultTokens).toBeNull();
    expect(result.responsive).toEqual(DEFAULT_RESPONSIVE);
    expect(result.advanced).toEqual(DEFAULT_ADVANCED);
  });

  it("uses cached component version when available", () => {
    const cache = new Map<number, VersionResponse>();
    const mockVersion = {
      slot_definitions: [
        {
          slot_id: "hero",
          slot_type: "body",
          selector: "[data-slot-name='hero']",
          required: true,
          max_chars: 200,
          placeholder: "Enter hero text",
          label: "Hero",
        },
      ],
      default_tokens: { background_color: "#ffffff" },
    } as unknown as VersionResponse;
    cache.set(42, mockVersion);

    const node = makeSectionNode({ componentId: 42 });
    const result = sectionNodeToBuilderSection(node, cache);

    expect(result.slotDefinitions).toHaveLength(1);
    expect(result.slotDefinitions[0]?.slot_id).toBe("hero");
    expect(result.defaultTokens).toEqual({ background_color: "#ffffff" });
  });

  it("falls back to inference when componentId not in cache", () => {
    const cache = new Map<number, VersionResponse>();
    const node = makeSectionNode({
      componentId: 99,
      htmlFragment: '<table><tr><td><a data-slot-name="link" href="#">Go</a></td></tr></table>',
    });
    const result = sectionNodeToBuilderSection(node, cache);

    expect(result.slotDefinitions).toHaveLength(1);
    expect(result.slotDefinitions[0]?.slot_type).toBe("cta");
  });

  it("preserves slotFills from node.slotValues", () => {
    const node = makeSectionNode({
      slotValues: { headline: "Custom text" },
    });
    const result = sectionNodeToBuilderSection(node);
    expect(result.slotFills).toEqual({ headline: "Custom text" });
  });
});
