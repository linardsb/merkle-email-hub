import { describe, it, expect } from "vitest";
import { compileMjml, mjmlVersion } from "./mjml-compile.js";

/**
 * Dedicated MJML compilation tests (Phase 35.11).
 * Covers edge cases beyond the basic happy-path tests in index.test.js.
 */

describe("compileMjml", () => {
  it("valid MJML produces HTML with table layout", () => {
    const { html, errors } = compileMjml(`
      <mjml>
        <mj-body>
          <mj-section>
            <mj-column>
              <mj-text>Hello world</mj-text>
            </mj-column>
          </mj-section>
        </mj-body>
      </mjml>
    `);

    expect(html).toContain("<table");
    expect(html).toContain("Hello world");
    expect(errors).toHaveLength(0);
  });

  it("invalid MJML tag produces errors array", () => {
    const { errors } = compileMjml(`
      <mjml>
        <mj-body>
          <mj-custom-invalid>Content</mj-custom-invalid>
        </mj-body>
      </mjml>
    `);

    expect(errors.length).toBeGreaterThan(0);
  });

  it("empty string throws a parsing error", () => {
    // MJML parser throws on empty/non-MJML input
    expect(() => compileMjml("")).toThrow();
  });

  it("large MJML with 20 sections compiles successfully", () => {
    const sections = Array.from(
      { length: 20 },
      (_, i) => `
        <mj-section>
          <mj-column>
            <mj-text>Section ${i + 1}</mj-text>
          </mj-column>
        </mj-section>`,
    ).join("\n");

    const mjml = `<mjml><mj-body>${sections}</mj-body></mjml>`;
    const { html, errors } = compileMjml(mjml);

    expect(html).toContain("Section 1");
    expect(html).toContain("Section 20");
    expect(errors).toHaveLength(0);
  });

  it("preserves inline styles from mj-text", () => {
    const { html } = compileMjml(`
      <mjml>
        <mj-body>
          <mj-section>
            <mj-column>
              <mj-text color="red" font-size="20px">Styled text</mj-text>
            </mj-column>
          </mj-section>
        </mj-body>
      </mjml>
    `);

    expect(html).toContain("color:red");
    expect(html).toContain("font-size:20px");
  });

  it("generates MSO conditionals for Outlook", () => {
    const { html } = compileMjml(`
      <mjml>
        <mj-body>
          <mj-section>
            <mj-column>
              <mj-text>Content</mj-text>
            </mj-column>
          </mj-section>
        </mj-body>
      </mjml>
    `);

    expect(html).toContain("<!--[if mso");
  });

  it("multi-column produces responsive layout", () => {
    const { html } = compileMjml(`
      <mjml>
        <mj-body>
          <mj-section>
            <mj-column width="33.33%">
              <mj-text>Col 1</mj-text>
            </mj-column>
            <mj-column width="33.33%">
              <mj-text>Col 2</mj-text>
            </mj-column>
            <mj-column width="33.33%">
              <mj-text>Col 3</mj-text>
            </mj-column>
          </mj-section>
        </mj-body>
      </mjml>
    `);

    expect(html).toContain("Col 1");
    expect(html).toContain("Col 2");
    expect(html).toContain("Col 3");
    // MJML generates responsive media queries
    expect(html).toContain("@media");
  });

  it("mjmlVersion is a semver string", () => {
    expect(typeof mjmlVersion).toBe("string");
    expect(mjmlVersion).toMatch(/^\d+\.\d+\.\d+/);
  });
});
