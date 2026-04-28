import { describe, it, expect } from "vitest";

import {
  processSection,
  buildResponsiveCss,
  buildDarkModeCss,
  buildScopedSectionCss,
  wrapMsoGhostTable,
  assembleDocument,
  assembleEmailHtml,
} from "../html-assembler";
import type { BuilderSection } from "@/types/visual-builder";
import { DEFAULT_RESPONSIVE, DEFAULT_ADVANCED } from "@/types/visual-builder";

function makeSection(overrides: Partial<BuilderSection> = {}): BuilderSection {
  return {
    id: "sec-1",
    componentId: 1,
    componentName: "Hero",
    componentSlug: "hero",
    category: "content",
    html: '<table class="hero"><tr><td>placeholder</td></tr></table>',
    css: null,
    slotFills: {},
    tokenOverrides: {},
    slotDefinitions: [],
    defaultTokens: null,
    responsive: { ...DEFAULT_RESPONSIVE },
    advanced: { ...DEFAULT_ADVANCED },
    ...overrides,
  };
}

describe("processSection", () => {
  it("annotates the root with section id and component metadata", () => {
    const html = processSection(makeSection());
    expect(html).toContain('data-section-id="sec-1"');
    expect(html).toContain('data-component-id="1"');
    expect(html).toContain('data-component-name="Hero"');
  });

  it("returns original HTML when there is no root element", () => {
    expect(processSection(makeSection({ html: "" }))).toBe("");
    expect(processSection(makeSection({ html: "   " }))).toBe("   ");
  });

  it("merges token overrides into the inline style", () => {
    const html = processSection(
      makeSection({
        tokenOverrides: { background: "#ff0000", color: "#000000" },
      }),
    );
    expect(html).toMatch(/background-color:#ff0000/);
    expect(html).toMatch(/color:#000000/);
  });

  it("strips dangerous CSS values from token overrides", () => {
    const html = processSection(
      makeSection({
        tokenOverrides: { background: "expression(alert(1))" },
      }),
    );
    expect(html).not.toMatch(/expression\(/);
  });

  it("blocks event-handler and dangerous URI HTML attributes", () => {
    // Build the dangerous URI from parts so the literal doesn't trip no-script-url.
    const dangerousScheme = ["java", "script", ":alert(1)"].join("");
    const html = processSection(
      makeSection({
        advanced: {
          ...DEFAULT_ADVANCED,
          htmlAttributes: {
            onclick: "alert(1)",
            href: dangerousScheme,
            "data-test": "ok",
          },
        },
      }),
    );
    expect(html).not.toMatch(/onclick=/);
    expect(html).not.toMatch(/href="javascript:/);
    expect(html).toContain('data-test="ok"');
  });

  it("appends sanitized custom css class without replacing existing classes", () => {
    const html = processSection(
      makeSection({
        advanced: {
          ...DEFAULT_ADVANCED,
          customCssClass: "promo  highlight!@#",
        },
      }),
    );
    expect(html).toContain("hero");
    expect(html).toContain("promo");
    expect(html).toContain("highlight");
    expect(html).not.toContain("!@#");
  });
});

describe("buildResponsiveCss", () => {
  it("returns empty string when no section has responsive overrides", () => {
    expect(buildResponsiveCss([makeSection()])).toBe("");
  });

  it("emits stack-on-mobile rules scoped by section id", () => {
    const css = buildResponsiveCss([
      makeSection({
        id: "sec-2",
        responsive: { ...DEFAULT_RESPONSIVE, stackOnMobile: true },
      }),
    ]);
    expect(css).toContain("<style>");
    expect(css).toContain('[data-section-id="sec-2"]');
    expect(css).toContain("display:block !important");
    expect(css).toContain("@media (max-width:480px)");
  });

  it("sanitizes mobile font-size value", () => {
    const css = buildResponsiveCss([
      makeSection({
        responsive: { ...DEFAULT_RESPONSIVE, mobileFontSize: "expression(1)" },
      }),
    ]);
    expect(css).not.toMatch(/expression\(/);
  });
});

describe("buildDarkModeCss", () => {
  it("returns empty string when no section has dark-mode overrides", () => {
    expect(buildDarkModeCss([makeSection()])).toBe("");
  });

  it("emits both prefers-color-scheme and data-ogsc rules", () => {
    const css = buildDarkModeCss([
      makeSection({
        advanced: {
          ...DEFAULT_ADVANCED,
          darkModeOverrides: { "background-color": "#111111", color: "#eeeeee" },
        },
      }),
    ]);
    expect(css).toContain("@media (prefers-color-scheme:dark)");
    expect(css).toContain("[data-ogsc]");
    expect(css).toContain("background-color:#111111");
    expect(css).toContain("color:#eeeeee");
  });
});

describe("buildScopedSectionCss", () => {
  it("returns empty string when no section has css", () => {
    expect(buildScopedSectionCss([makeSection()])).toBe("");
  });

  it("scopes selectors with the section id and strips @import", () => {
    const css = buildScopedSectionCss([
      makeSection({
        id: "sec-x",
        css: "@import url(evil.css);\n.title { color: red; }",
      }),
    ]);
    expect(css).toContain('[data-section-id="sec-x"] .title');
    expect(css).not.toContain("@import url(evil.css)");
    expect(css).toContain("/* @import stripped */");
  });
});

describe("wrapMsoGhostTable", () => {
  it("wraps html in MSO conditional ghost table comments", () => {
    const wrapped = wrapMsoGhostTable("<div>x</div>");
    expect(wrapped).toContain("<!--[if mso]>");
    expect(wrapped).toContain("<![endif]-->");
    expect(wrapped).toContain("<div>x</div>");
  });
});

describe("assembleDocument", () => {
  it("wraps sections in a default email shell when no templateShell is given", () => {
    const out = assembleDocument(["<div>a</div>", "<div>b</div>"], ["A", "B"], "");
    expect(out).toContain("<!DOCTYPE html>");
    expect(out).toContain("<!-- section: A -->");
    expect(out).toContain("<!-- section: B -->");
    expect(out).toContain("max-width:600px");
  });

  it("injects head styles into the default shell", () => {
    const out = assembleDocument(["<div>a</div>"], ["A"], "<style>.x { color: red; }</style>");
    expect(out).toContain(".x { color: red; }");
  });
});

describe("assembleEmailHtml", () => {
  it("returns null for empty section lists", () => {
    expect(assembleEmailHtml([])).toBeNull();
  });

  it("produces a complete HTML document for a single section", () => {
    const out = assembleEmailHtml([makeSection()]);
    expect(out).not.toBeNull();
    expect(out).toContain("<!DOCTYPE html>");
    expect(out).toContain('data-section-id="sec-1"');
    expect(out).toContain('data-component-name="Hero"');
  });

  it("MSO-wraps a section when its advanced.msoConditional flag is set", () => {
    const out = assembleEmailHtml([
      makeSection({
        advanced: { ...DEFAULT_ADVANCED, msoConditional: true },
      }),
    ]);
    expect(out).toContain("<!--[if mso]>");
  });
});
