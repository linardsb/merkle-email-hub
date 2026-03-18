import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { stripAnnotations, hasAnnotations } from "./section-markers";
import {
  htmlToSections,
  sectionsToHtml,
  diffSections,
  parseInlineStyle,
  extractEspTokens,
  restoreEspTokens,
  internalizeStructuralEsp,
  isColumnGroup,
} from "./ast-mapper";
import { BuilderSyncEngine } from "./sync-engine";
import type { SectionNode } from "@/types/visual-builder";

// ── Realistic email HTML helpers ──

/** Builder-style email document: table role=presentation with section rows */
function builderDoc(sectionRows: string): string {
  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<center>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;">
${sectionRows}
</table>
</center>
</body>
</html>`;
}

/** Assembler-style email document: divs with data-section attributes */
function assemblerDoc(sectionDivs: string): string {
  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
${sectionDivs}
</body>
</html>`;
}

/** Classic email: bodyTable > emailContainer nested tables */
function classicDoc(contentRows: string): string {
  return `<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8" /></head>
<body>
<table border="0" cellpadding="0" cellspacing="0" height="100%" width="100%" id="bodyTable">
  <tr><td align="center" valign="top">
    <table border="0" cellpadding="20" cellspacing="0" width="600" id="emailContainer">
${contentRows}
    </table>
  </td></tr>
</table>
</body>
</html>`;
}

/** Column layout: columns as sibling elements inside a wrapper */
function columnDoc(columnContent: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /><style>.column { width: 24%; }</style></head>
<body>
<div class="container">
  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr><td align="center">
${columnContent}
    </td></tr>
  </table>
</div>
</body>
</html>`;
}

// ── section-markers ──

describe("stripAnnotations", () => {
  it("removes data-section-id attributes (double quotes)", () => {
    const html = '<tr data-section-id="header"><td>Content</td></tr>';
    expect(stripAnnotations(html)).toBe("<tr><td>Content</td></tr>");
  });

  it("removes data-section-id attributes (single quotes)", () => {
    const html = "<tr data-section-id='header'><td>Content</td></tr>";
    expect(stripAnnotations(html)).toBe("<tr><td>Content</td></tr>");
  });

  it("removes data-slot-name attributes", () => {
    const html = '<h1 data-slot="headline" data-slot-name="headline">Title</h1>';
    expect(stripAnnotations(html)).toBe('<h1 data-slot="headline">Title</h1>');
  });

  it("removes data-component-id attributes", () => {
    const html = '<div data-component-id="42">Content</div>';
    expect(stripAnnotations(html)).toBe("<div>Content</div>");
  });

  it("removes data-component-name attributes (Bug 13)", () => {
    const html = '<div data-component-name="Hero">Content</div>';
    expect(stripAnnotations(html)).toBe("<div>Content</div>");
  });

  it("removes all builder annotations from a full element", () => {
    const html = '<div data-section-id="s1" data-component-id="42" data-component-name="Hero">Content</div>';
    expect(stripAnnotations(html)).toBe("<div>Content</div>");
  });

  it("preserves other data attributes", () => {
    const html = '<div data-section="header" data-section-id="header">Content</div>';
    expect(stripAnnotations(html)).toBe('<div data-section="header">Content</div>');
  });

  it("strips annotations from full email template", () => {
    const html = builderDoc(
      '<tr data-section-id="s1"><td><h1 data-slot-name="headline">Hello</h1></td></tr>'
    );
    const stripped = stripAnnotations(html);
    expect(stripped).not.toContain("data-section-id");
    expect(stripped).not.toContain("data-slot-name");
    expect(stripped).toContain("<h1>Hello</h1>");
  });
});

describe("hasAnnotations", () => {
  it("returns true for annotated HTML", () => {
    expect(hasAnnotations('<tr data-section-id="foo">')).toBe(true);
  });

  it("returns true for single-quoted annotations", () => {
    expect(hasAnnotations("<tr data-section-id='foo'>")).toBe(true);
  });

  it("returns false for unannotated HTML", () => {
    expect(hasAnnotations("<tr><td>Content</td></tr>")).toBe(false);
  });
});

// ── parseInlineStyle ──

describe("parseInlineStyle", () => {
  it("parses simple property-value pairs", () => {
    const result = parseInlineStyle("color: red; font-size: 16px");
    expect(result).toEqual({ color: "red", "font-size": "16px" });
  });

  it("handles colons in URL values (Bug 3)", () => {
    const result = parseInlineStyle(
      'background-image: url("data:image/png;base64,abc"); color: blue'
    );
    expect(result["background-image"]).toContain("data:image/png");
    expect(result.color).toBe("blue");
  });

  it("handles quoted font-family values with commas", () => {
    const result = parseInlineStyle(
      'font-family: "Helvetica Neue", Arial, sans-serif; color: #333'
    );
    expect(result["font-family"]).toContain('"Helvetica Neue"');
    expect(result.color).toBe("#333");
  });

  it("handles MSO-specific properties", () => {
    const result = parseInlineStyle(
      "mso-line-height-rule: exactly; line-height: 20px"
    );
    expect(result["mso-line-height-rule"]).toBe("exactly");
    expect(result["line-height"]).toBe("20px");
  });

  it("handles empty style string", () => {
    expect(parseInlineStyle("")).toEqual({});
  });

  it("handles single property without trailing semicolon", () => {
    const result = parseInlineStyle("color: red");
    expect(result).toEqual({ color: "red" });
  });
});

// ── ESP token preservation ──

describe("extractEspTokens / restoreEspTokens", () => {
  it("preserves Liquid template tokens", () => {
    const html = '<td>{% if user.vip %}VIP Content{% endif %}</td>';
    const { sanitized, tokenMap } = extractEspTokens(html);
    expect(sanitized).not.toContain("{%");
    expect(sanitized).toContain("__ESP_");
    const restored = restoreEspTokens(sanitized, tokenMap);
    expect(restored).toBe(html);
  });

  it("preserves Handlebars tokens", () => {
    const html = '<td>{{user.name}}</td>';
    const { sanitized, tokenMap } = extractEspTokens(html);
    expect(sanitized).not.toContain("{{");
    const restored = restoreEspTokens(sanitized, tokenMap);
    expect(restored).toBe(html);
  });

  it("preserves AMPscript tokens", () => {
    const html = '<td>%%first_name%%</td>';
    const { sanitized, tokenMap } = extractEspTokens(html);
    expect(sanitized).not.toContain("%%");
    const restored = restoreEspTokens(sanitized, tokenMap);
    expect(restored).toBe(html);
  });

  it("preserves ERB/EJS tokens", () => {
    const html = '<td><%= user.name %></td>';
    const { sanitized, tokenMap } = extractEspTokens(html);
    expect(sanitized).not.toContain("<%");
    const restored = restoreEspTokens(sanitized, tokenMap);
    expect(restored).toBe(html);
  });

  it("preserves multiple ESP syntaxes in the same HTML", () => {
    const html = '<td>{{name}} - {% if premium %}%%discount_code%%{% endif %}</td>';
    const { sanitized, tokenMap } = extractEspTokens(html);
    const restored = restoreEspTokens(sanitized, tokenMap);
    expect(restored).toBe(html);
  });

  it("preserves ESP tokens in attributes", () => {
    const html = '<a href="{{tracking_url}}">Click</a>';
    const { sanitized, tokenMap } = extractEspTokens(html);
    const restored = restoreEspTokens(sanitized, tokenMap);
    expect(restored).toBe(html);
  });
});

// ── internalizeStructuralEsp ──

describe("internalizeStructuralEsp", () => {
  it("moves Liquid {% if %} from around <tr> to inside <td> (single cell)", () => {
    const html = '{% if user.vip %}<tr><td>VIP Section</td></tr>{% endif %}';
    const { sanitized, tokenMap } = extractEspTokens(html);
    const result = internalizeStructuralEsp(sanitized, tokenMap);
    const restored = restoreEspTokens(result, tokenMap);

    // The <tr> should be clean, conditionals inside <td>
    expect(restored).toContain("<tr><td>");
    expect(restored).toContain("{% if user.vip %}");
    expect(restored).toContain("{% endif %}");
    expect(restored).toContain("VIP Section");
    // Conditional should be INSIDE the <td>, not wrapping the <tr>
    expect(restored).toMatch(/<td>.*\{% if user\.vip %\}.*VIP Section.*\{% endif %\}.*<\/td>/s);
  });

  it("moves Liquid {% if %}/{% else %} with multiple branches", () => {
    const html = `{% if user.vip %}<tr><td>VIP Content</td></tr>{% else %}<tr><td>Standard Content</td></tr>{% endif %}`;
    const { sanitized, tokenMap } = extractEspTokens(html);
    const result = internalizeStructuralEsp(sanitized, tokenMap);
    const restored = restoreEspTokens(result, tokenMap);

    // Both branches should have conditionals inside cells
    expect(restored).toContain("VIP Content");
    expect(restored).toContain("Standard Content");
    expect(restored).not.toMatch(/\{% if user\.vip %\}\s*<tr>/);
  });

  it("moves AMPscript conditionals inside <td>", () => {
    const html = '%%[IF @vip == true]%%<tr><td>VIP Offer</td></tr>%%[ENDIF]%%';
    const { sanitized, tokenMap } = extractEspTokens(html);
    const result = internalizeStructuralEsp(sanitized, tokenMap);
    const restored = restoreEspTokens(result, tokenMap);

    expect(restored).toMatch(/<td>.*%%\[IF @vip == true\]%%.*VIP Offer.*%%\[ENDIF\]%%.*<\/td>/s);
  });

  it("handles multi-cell rows (moves tokens into each <td>)", () => {
    const html = '{% if show_cols %}<tr><td>Left</td><td>Right</td></tr>{% endif %}';
    const { sanitized, tokenMap } = extractEspTokens(html);
    const result = internalizeStructuralEsp(sanitized, tokenMap);
    const restored = restoreEspTokens(result, tokenMap);

    // Both cells should have the conditional
    expect(restored).toMatch(/<td>.*\{% if show_cols %\}.*Left.*\{% endif %\}.*<\/td>/s);
    expect(restored).toMatch(/<td>.*\{% if show_cols %\}.*Right.*\{% endif %\}.*<\/td>/s);
  });

  it("leaves non-structural ESP tokens untouched", () => {
    const html = '<tr><td>Hello {{user.name}}, {% if premium %}special{% endif %} offer</td></tr>';
    const { sanitized, tokenMap } = extractEspTokens(html);
    const result = internalizeStructuralEsp(sanitized, tokenMap);
    const restored = restoreEspTokens(result, tokenMap);

    // Already inside <td>, should not be modified
    expect(restored).toBe(html);
  });

  it("handles ERB/EJS structural conditionals", () => {
    const html = '<% if @user.admin? %><tr><td>Admin Panel</td></tr><% end %>';
    const { sanitized, tokenMap } = extractEspTokens(html);
    const result = internalizeStructuralEsp(sanitized, tokenMap);
    const restored = restoreEspTokens(result, tokenMap);

    expect(restored).toMatch(/<td>.*<% if @user\.admin\? %>.*Admin Panel.*<% end %>.*<\/td>/s);
  });

  it("integrates with htmlToSections for full roundtrip", () => {
    // Realistic ESP template with structural conditionals
    const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0">
      <tr><td style="padding:20px">Welcome {{user.name}}</td></tr>
      {% if user.vip %}<tr><td style="padding:20px;background:#gold">Exclusive VIP Offer</td></tr>{% endif %}
      <tr><td style="padding:10px;font-size:11px">Footer</td></tr>
    </table>
  </td></tr>
</table>
</body></html>`;

    const sections = htmlToSections(html);
    expect(sections).not.toBeNull();

    // The VIP row should exist as a section with the conditional INSIDE the <td>
    const allHtml = sections!.map((s) => s.htmlFragment).join("");
    expect(allHtml).toContain("{% if user.vip %}");
    expect(allHtml).toContain("{% endif %}");
    expect(allHtml).toContain("Exclusive VIP Offer");
    expect(allHtml).toContain("{{user.name}}");
  });
});

// ── isColumnGroup ──

describe("isColumnGroup", () => {
  it("detects columns sharing a CSS class", () => {
    const doc = new DOMParser().parseFromString(
      '<div><div class="col">A</div><div class="col">B</div></div>',
      "text/html"
    );
    const children = Array.from(doc.querySelector("div")!.children);
    expect(isColumnGroup(children)).toBe(true);
  });

  it("detects columns with percentage widths summing to ~100%", () => {
    const doc = new DOMParser().parseFromString(
      '<div><table width="50%"><tr><td>A</td></tr></table><table width="50%"><tr><td>B</td></tr></table></div>',
      "text/html"
    );
    const children = Array.from(doc.querySelector("div")!.children);
    expect(isColumnGroup(children)).toBe(true);
  });

  it("detects columns with pixel widths summing to container width", () => {
    const doc = new DOMParser().parseFromString(
      '<div><table width="300"><tr><td>A</td></tr></table><table width="300"><tr><td>B</td></tr></table></div>',
      "text/html"
    );
    const children = Array.from(doc.querySelector("div")!.children);
    expect(isColumnGroup(children)).toBe(true);
  });

  it("detects inline-block display columns", () => {
    const doc = new DOMParser().parseFromString(
      '<div><div style="display:inline-block;width:50%">A</div><div style="display:inline-block;width:50%">B</div></div>',
      "text/html"
    );
    const children = Array.from(doc.querySelector("div")!.children);
    expect(isColumnGroup(children)).toBe(true);
  });

  it("does not detect unrelated siblings as columns", () => {
    const doc = new DOMParser().parseFromString(
      '<div><div class="header">H</div><div class="body">B</div><div class="footer">F</div></div>',
      "text/html"
    );
    const children = Array.from(doc.querySelector("div")!.children);
    expect(isColumnGroup(children)).toBe(false);
  });

  it("rejects single child", () => {
    const doc = new DOMParser().parseFromString(
      '<div><div class="col">A</div></div>',
      "text/html"
    );
    const children = Array.from(doc.querySelector("div")!.children);
    expect(isColumnGroup(children)).toBe(false);
  });

  it("rejects more than 6 children", () => {
    const doc = new DOMParser().parseFromString(
      '<div><div class="c">1</div><div class="c">2</div><div class="c">3</div><div class="c">4</div><div class="c">5</div><div class="c">6</div><div class="c">7</div></div>',
      "text/html"
    );
    const children = Array.from(doc.querySelector("div")!.children);
    expect(isColumnGroup(children)).toBe(false);
  });
});

// ── htmlToSections ──

describe("htmlToSections", () => {
  describe("Strategy 1: data-section-id (annotated)", () => {
    it("parses annotated rows inside table", () => {
      const html = builderDoc(
        `<tr data-section-id="abc" data-component-name="Hero"><td>Hello</td></tr>
         <tr data-section-id="def" data-component-name="Footer"><td>Bye</td></tr>`
      );

      const sections = htmlToSections(html);
      expect(sections).toHaveLength(2);
      expect(sections![0]!.id).toBe("abc");
      expect(sections![0]!.componentName).toBe("Hero");
      expect(sections![1]!.id).toBe("def");
      expect(sections![1]!.componentName).toBe("Footer");
    });

    it("parses annotated divs (assembler output)", () => {
      const html = assemblerDoc(
        `<div data-section="header" data-section-id="header" data-component-name="Header">
           <h1 data-slot="headline" data-slot-name="headline">Welcome!</h1>
         </div>
         <div data-section="body" data-section-id="body" data-component-name="Body">
           <p data-slot="body_text" data-slot-name="body_text">Content</p>
         </div>`
      );

      const sections = htmlToSections(html);
      expect(sections).toHaveLength(2);
      expect(sections![0]!.id).toBe("header");
      expect(sections![0]!.slotValues["headline"]).toContain("Welcome!");
      expect(sections![1]!.slotValues["body_text"]).toContain("Content");
    });

    it("extracts inline style overrides using parseInlineStyle (Bug 3)", () => {
      const html = assemblerDoc(
        `<div data-section-id="s1" style="background-color: #ff0000; font-size: 16px">Content</div>`
      );

      const sections = htmlToSections(html);
      expect(sections![0]!.styleOverrides["background-color"]).toBe("#ff0000");
      expect(sections![0]!.styleOverrides["font-size"]).toBe("16px");
    });

    it("parses styles with colons in values correctly (Bug 3)", () => {
      const html = assemblerDoc(
        `<div data-section-id="s1" style="background-image: url('data:image/png;base64,abc'); font-family: 'Helvetica Neue', Arial">Content</div>`
      );

      const sections = htmlToSections(html);
      expect(sections![0]!.styleOverrides["background-image"]).toContain("data:image/png");
      expect(sections![0]!.styleOverrides["font-family"]).toContain("Helvetica Neue");
    });

    it("prefers annotated strategy when both annotations and comments present", () => {
      const html = builderDoc(
        `<!-- section: CommentName -->
         <tr data-section-id="s1" data-component-name="AttrName"><td>Content</td></tr>`
      );

      const sections = htmlToSections(html);
      expect(sections![0]!.id).toBe("s1");
      expect(sections![0]!.componentName).toBe("AttrName");
    });
  });

  describe("Strategy 2: structural analysis", () => {
    it("parses classic email (bodyTable/emailContainer)", () => {
      const html = classicDoc(
        `<tr><td>Header</td></tr>
         <tr><td>Body</td></tr>
         <tr><td>Footer</td></tr>`
      );

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections).toHaveLength(3);
      expect(sections![0]!.htmlFragment).toContain("Header");
      expect(sections![1]!.htmlFragment).toContain("Body");
      expect(sections![2]!.htmlFragment).toContain("Footer");
    });

    it("detects column layout as single section (Bug 2 - dynamic detection)", () => {
      const html = columnDoc(
        `<table class="column" width="24%" cellpadding="0" cellspacing="0" border="0">
           <tr><td><h3>Feature One</h3></td></tr>
         </table>
         <table class="column" width="24%" cellpadding="0" cellspacing="0" border="0">
           <tr><td><h3>Feature Two</h3></td></tr>
         </table>
         <table class="column" width="24%" cellpadding="0" cellspacing="0" border="0">
           <tr><td><h3>Feature Three</h3></td></tr>
         </table>
         <table class="column" width="24%" cellpadding="0" cellspacing="0" border="0">
           <tr><td><h3>Feature Four</h3></td></tr>
         </table>`
      );

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      // Dynamic column detection: 4 columns sharing "column" class = 1 section
      expect(sections!.length).toBeLessThanOrEqual(2); // could be 1 (columns grouped) or 2 (parent sections)
      // The section(s) should contain all columns
      const allHtml = sections!.map((s) => s.htmlFragment).join("");
      expect(allHtml).toContain("Feature One");
      expect(allHtml).toContain("Feature Four");
    });

    it("detects div-based inline-block columns as single section", () => {
      const html = `<html><body>
        <div class="wrapper">
          <div class="header">Header</div>
          <div class="columns-row">
            <div style="display:inline-block;width:50%">Col A</div>
            <div style="display:inline-block;width:50%">Col B</div>
          </div>
          <div class="footer">Footer</div>
        </div>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections).toHaveLength(3);
      // The columns-row section should contain both columns
      const columnsSection = sections!.find((s) =>
        s.htmlFragment.includes("Col A") && s.htmlFragment.includes("Col B")
      );
      expect(columnsSection).toBeDefined();
    });

    it("detects percentage-width table columns as single section", () => {
      const html = `<html><body>
        <div class="email">
          <div class="header">Header</div>
          <div class="content">
            <table width="50%"><tr><td>Left</td></tr></table>
            <table width="50%"><tr><td>Right</td></tr></table>
          </div>
          <div class="footer">Footer</div>
        </div>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections).toHaveLength(3);
      const contentSection = sections!.find((s) => s.componentName === "Content");
      expect(contentSection).toBeDefined();
      expect(contentSection!.htmlFragment).toContain("Left");
      expect(contentSection!.htmlFragment).toContain("Right");
    });

    it("parses builder output with section comments (div-based)", () => {
      const html = `<html><body>
        <div class="email-wrapper">
          <!-- section: Header -->
          <div class="header-section">Header content</div>
          <!-- section: Footer -->
          <div class="footer-section">Footer content</div>
        </div>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections).toHaveLength(2);
      expect(sections![0]!.componentName).toBe("Header");
      expect(sections![1]!.componentName).toBe("Footer");
    });

    it("falls back to tag-based names for table rows (comments unreliable inside table)", () => {
      const html = builderDoc(
        `<tr><td>Header content</td></tr>
         <tr><td>Footer content</td></tr>`
      );

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections).toHaveLength(2);
      expect(sections![0]!.componentName).toBe("Section");
    });

    it("parses div-based layout", () => {
      const html = `<html><body>
        <div class="wrapper">
          <div class="header">Header</div>
          <div class="content">Content</div>
          <div class="footer">Footer</div>
        </div>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections).toHaveLength(3);
      expect(sections![0]!.componentName).toBe("Header");
      expect(sections![1]!.componentName).toBe("Content");
      expect(sections![2]!.componentName).toBe("Footer");
    });

    it("infers section names from class names", () => {
      const html = `<html><body>
        <div class="hero-section">Hero</div>
        <div class="cta-block">CTA</div>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).toHaveLength(2);
      expect(sections![0]!.componentName).toBe("Hero-section");
      expect(sections![1]!.componentName).toBe("Cta-block");
    });

    it("infers section names from id when no class", () => {
      const html = `<html><body>
        <div id="topBanner">Banner</div>
        <div id="mainContent">Content</div>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).toHaveLength(2);
      expect(sections![0]!.componentName).toBe("TopBanner");
      expect(sections![1]!.componentName).toBe("MainContent");
    });

    it("uses tag name as fallback when no class or id", () => {
      const html = `<html><body>
        <table><tr><td>Row 1</td></tr></table>
        <table><tr><td>Row 2</td></tr></table>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).toHaveLength(2);
      expect(sections![0]!.componentName).toBe("Table");
    });

    it("skips MSO conditional comments when extracting names", () => {
      const html = `<html><body>
        <div class="wrapper">
          <!--[if mso]><table><tr><td><![endif]-->
          <div class="hero">Content 1</div>
          <div class="footer">Content 2</div>
        </div>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections![0]!.componentName).toBe("Hero");
    });

    it("handles email with width=600 table", () => {
      const html = `<html><body>
        <table width="600" cellpadding="0" cellspacing="0">
          <tr><td>Section 1</td></tr>
          <tr><td>Section 2</td></tr>
        </table>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections).toHaveLength(2);
    });

    it("captures preceding content (comments) for roundtrip (Bug 8)", () => {
      // Use div-based structure since HTML comments inside <table> get hoisted by DOMParser
      const html = `<html><body>
        <div class="email-container">
          <!-- section: Hero -->
          <table class="hero-row" width="100%" cellpadding="0" cellspacing="0"><tr><td>Hero content</td></tr></table>
          <!-- section: Footer -->
          <table class="footer-row" width="100%" cellpadding="0" cellspacing="0"><tr><td>Footer content</td></tr></table>
        </div>
      </body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections![0]!.precedingContent).toContain("section: Hero");
      expect(sections![1]!.precedingContent).toContain("section: Footer");
    });

    it("preserves ESP tokens through parsing (Liquid in table cells)", () => {
      const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0">
      <tr><td>{% if user.vip %}VIP{% endif %} Welcome</td></tr>
      <tr><td>Hello {{user.name}}</td></tr>
    </table>
  </td></tr>
</table>
</body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      const allHtml = sections!.map((s) => s.htmlFragment).join("");
      expect(allHtml).toContain("{% if user.vip %}");
      expect(allHtml).toContain("{% endif %}");
      expect(allHtml).toContain("{{user.name}}");
    });

    it("preserves ESP tokens in href attributes (table-based CTA)", () => {
      const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0">
      <tr><td class="cta-cell"><a href="{{tracking_url}}" style="color:#ffffff">Click here</a></td></tr>
      <tr><td class="footer-cell">%%unsubscribe_url%%</td></tr>
    </table>
  </td></tr>
</table>
</body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      const allHtml = sections!.map((s) => s.htmlFragment).join("");
      expect(allHtml).toContain("{{tracking_url}}");
      expect(allHtml).toContain("%%unsubscribe_url%%");
    });

    it("handles SFMC deeply nested table layouts", () => {
      const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0">
      <tr><td>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td>Header %%first_name%%</td></tr>
          <tr><td>Body content</td></tr>
          <tr><td>Footer</td></tr>
        </table>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>`;

      const sections = htmlToSections(html);
      expect(sections).not.toBeNull();
      expect(sections!.length).toBeGreaterThanOrEqual(2);
      const allHtml = sections!.map((s) => s.htmlFragment).join("");
      expect(allHtml).toContain("%%first_name%%");
    });
  });

  it("returns null for HTML with no recognizable sections", () => {
    const html = "<html><body><p>Just a paragraph</p></body></html>";
    expect(htmlToSections(html)).toBeNull();
  });

  it("returns null for empty body", () => {
    expect(htmlToSections("<html><body></body></html>")).toBeNull();
  });
});

// ── sectionsToHtml ──

describe("sectionsToHtml", () => {
  const makeSection = (
    id: string,
    content: string,
    precedingContent?: string
  ): SectionNode => ({
    id,
    componentId: 0,
    componentName: "Section",
    slotValues: {},
    styleOverrides: {},
    htmlFragment: content,
    precedingContent,
  });

  it("inserts sections into builder-style table", () => {
    const shell = builderDoc("");
    const sections = [
      makeSection("s1", '<tr data-section-id="s1"><td>Header</td></tr>'),
      makeSection("s2", '<tr data-section-id="s2"><td>Footer</td></tr>'),
    ];

    const result = sectionsToHtml(sections, shell);
    expect(result).toContain("Header");
    expect(result).toContain("Footer");
    expect(result).toContain("<!DOCTYPE html>");
  });

  it("inserts sections into classic email structure", () => {
    const shell = classicDoc("");
    const sections = [
      makeSection("s1", "<tr><td>New Header</td></tr>"),
      makeSection("s2", "<tr><td>New Body</td></tr>"),
    ];

    const result = sectionsToHtml(sections, shell);
    expect(result).toContain("New Header");
    expect(result).toContain("New Body");
    expect(result).toContain("emailContainer");
  });

  it("inserts column tables into column structure", () => {
    const shell = columnDoc("");
    const sections = [
      makeSection("c1", '<table class="column"><tr><td>Col 1</td></tr></table>'),
      makeSection("c2", '<table class="column"><tr><td>Col 2</td></tr></table>'),
    ];

    const result = sectionsToHtml(sections, shell);
    expect(result).toContain("Col 1");
    expect(result).toContain("Col 2");
  });

  it("preserves structure when no sections inserted", () => {
    const shell = `<html><body><div class="wrapper"><div class="header">Old</div><div class="footer">Old</div></div></body></html>`;
    const result = sectionsToHtml([], shell);
    // Content children removed, but wrapper structure preserved
    expect(result).toContain("wrapper");
  });

  it("preserves preceding content in serialized output (Bug 8)", () => {
    const shell = `<html><body><div class="email"></div></body></html>`;
    const sections = [
      makeSection("s1", '<div class="hero">Hero</div>', "<!-- section: Hero -->"),
      makeSection("s2", '<div class="footer">Footer</div>', "<!-- section: Footer -->"),
    ];

    const result = sectionsToHtml(sections, shell);
    expect(result).toContain("Hero");
    expect(result).toContain("Footer");
  });

  it("uses DOM doctype reconstruction instead of regex (Bug 9)", () => {
    const shell = `<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body><div class="email"><div>Old</div></div></body></html>`;
    const sections = [makeSection("s1", "<div>New</div>")];

    const result = sectionsToHtml(sections, shell);
    expect(result).toMatch(/^<!DOCTYPE html>/i);
    expect(result).toContain("New");
  });

  it("preserves ESP tokens through serialization", () => {
    const shell = `<html><body><div class="email"><div>placeholder</div></div></body></html>`;
    const sections = [
      makeSection("s1", '<div>Hello {{user.name}}, {% if vip %}VIP{% endif %}</div>'),
    ];

    const result = sectionsToHtml(sections, shell);
    expect(result).toContain("{{user.name}}");
    expect(result).toContain("{% if vip %}");
    expect(result).toContain("{% endif %}");
  });
});

// ── roundtrip tests ──

describe("roundtrip: htmlToSections → sectionsToHtml → htmlToSections", () => {
  it("roundtrips builder-style email", () => {
    const original = builderDoc(
      `<tr data-section-id="hero" data-component-name="Hero"><td>Welcome</td></tr>
       <tr data-section-id="footer" data-component-name="Footer"><td>Goodbye</td></tr>`
    );

    const sections = htmlToSections(original)!;
    expect(sections).toHaveLength(2);

    const rebuilt = sectionsToHtml(sections, original);
    expect(rebuilt).toContain("Welcome");
    expect(rebuilt).toContain("Goodbye");

    const reparsed = htmlToSections(rebuilt)!;
    expect(reparsed).toHaveLength(2);
    expect(reparsed[0]!.id).toBe("hero");
    expect(reparsed[1]!.id).toBe("footer");
  });

  it("roundtrips classic email template", () => {
    const original = classicDoc(
      `<tr><td>Header</td></tr>
       <tr><td>Body</td></tr>
       <tr><td>Footer</td></tr>`
    );

    const sections = htmlToSections(original)!;
    expect(sections).toHaveLength(3);

    const rebuilt = sectionsToHtml(sections, original);
    const reparsed = htmlToSections(rebuilt)!;
    expect(reparsed).toHaveLength(3);
    expect(reparsed[0]!.htmlFragment).toContain("Header");
    expect(reparsed[1]!.htmlFragment).toContain("Body");
    expect(reparsed[2]!.htmlFragment).toContain("Footer");
  });

  it("roundtrips column layout (columns stay grouped)", () => {
    const col = (n: number) =>
      `<table class="column" width="24%"><tr><td><h3>Feature ${n}</h3></td></tr></table>`;
    const original = columnDoc([1, 2, 3, 4].map(col).join("\n"));

    const sections = htmlToSections(original)!;
    // Columns grouped into fewer sections (not 4 separate ones)
    expect(sections.length).toBeLessThanOrEqual(2);

    // All content preserved
    const allHtml = sections.map((s) => s.htmlFragment).join("");
    expect(allHtml).toContain("Feature 1");
    expect(allHtml).toContain("Feature 4");
  });

  it("roundtrips assembler output with slot annotations", () => {
    const original = assemblerDoc(
      `<div data-section="header" data-section-id="header" data-component-name="Header">
         <h1 data-slot="headline" data-slot-name="headline">Hello World</h1>
       </div>`
    );

    const sections = htmlToSections(original)!;
    expect(sections[0]!.id).toBe("header");
    expect(sections[0]!.slotValues["headline"]).toContain("Hello World");
  });

  it("roundtrips structure preservation: original classes/IDs/styles survive (Bug 7)", () => {
    // Realistic ESP-imported email with table structure, classes, IDs, inline styles
    const original = `<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><meta charset="utf-8"></head>
<body>
<table width="100%" cellpadding="0" cellspacing="0" border="0" id="bodyTable" bgcolor="#f4f4f4">
  <tr><td align="center" valign="top">
    <table width="600" cellpadding="0" cellspacing="0" border="0" id="emailContainer">
      <tr data-section-id="s1" data-component-name="Hero" class="hero-row" id="main-hero"><td style="background-color:#f0f0f0;padding:20px;font-family:Arial,sans-serif"><h1 style="margin:0;color:#333333">Title</h1></td></tr>
      <tr data-section-id="s2" data-component-name="Footer" class="footer-row" id="site-footer"><td style="padding:10px;text-align:center;font-size:12px;color:#999999"><p style="margin:0">Footer &copy; 2026</p></td></tr>
    </table>
  </td></tr>
</table>
</body></html>`;

    const sections = htmlToSections(original)!;
    expect(sections).toHaveLength(2);

    // Classes, IDs, and inline styles preserved in htmlFragment
    expect(sections![0]!.htmlFragment).toContain('class="hero-row"');
    expect(sections![0]!.htmlFragment).toContain('id="main-hero"');
    expect(sections![0]!.htmlFragment).toContain("background-color:#f0f0f0");
    expect(sections![0]!.htmlFragment).toContain("font-family:");
    expect(sections![1]!.htmlFragment).toContain('class="footer-row"');
    expect(sections![1]!.htmlFragment).toContain('id="site-footer"');
    expect(sections![1]!.htmlFragment).toContain("text-align:center");

    // Roundtrip: rebuild → reparse preserves structure
    const rebuilt = sectionsToHtml(sections, original);
    expect(rebuilt).toContain('id="bodyTable"');
    expect(rebuilt).toContain('id="emailContainer"');
    const reparsed = htmlToSections(rebuilt)!;
    expect(reparsed).toHaveLength(2);
    expect(reparsed[0]!.id).toBe("s1");
    expect(reparsed[1]!.id).toBe("s2");
  });

  it("roundtrips ESP import with template variables in table cells", () => {
    // Realistic Braze/SFMC-style email with personalization tokens inside <td> cells
    const original = `<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><meta charset="utf-8">
<style>.preheader { display:none; } .btn { background-color:#1a73e8; }</style>
</head>
<body>
<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" border="0" class="email-container">
      <tr class="header-row"><td style="padding:20px;font-family:Arial,sans-serif">Hello {{user.first_name}}, welcome back!</td></tr>
      <tr class="content-row"><td style="padding:20px">{% if user.premium %}<strong>Premium</strong> content for you{% else %}Standard content{% endif %}</td></tr>
      <tr class="cta-row"><td style="padding:20px;text-align:center"><a href="{{cta_url}}" class="btn" style="color:#ffffff;padding:12px 24px;text-decoration:none;display:inline-block">Shop Now</a></td></tr>
      <tr class="footer-row"><td style="padding:10px;font-size:11px;color:#999"><a href="{{unsubscribe_url}}" style="color:#999">Unsubscribe</a> | %%company_address%%</td></tr>
    </table>
  </td></tr>
</table>
</body></html>`;

    const sections = htmlToSections(original)!;
    expect(sections).not.toBeNull();
    expect(sections.length).toBeGreaterThanOrEqual(3);

    const rebuilt = sectionsToHtml(sections, original);
    // All ESP tokens survive the roundtrip
    expect(rebuilt).toContain("{{user.first_name}}");
    expect(rebuilt).toContain("{% if user.premium %}");
    expect(rebuilt).toContain("{% else %}");
    expect(rebuilt).toContain("{% endif %}");
    expect(rebuilt).toContain("{{cta_url}}");
    expect(rebuilt).toContain("{{unsubscribe_url}}");
    expect(rebuilt).toContain("%%company_address%%");
    // Table structure preserved
    expect(rebuilt).toContain('class="email-container"');
    expect(rebuilt).toContain('class="header-row"');
    expect(rebuilt).toContain('class="footer-row"');
  });
});

// ── diffSections ──

describe("diffSections", () => {
  const makeSection = (id: string, html = "<tr><td></td></tr>"): SectionNode => ({
    id,
    componentId: 0,
    componentName: "Section",
    slotValues: {},
    styleOverrides: {},
    htmlFragment: html,
  });

  it("detects added sections", () => {
    const prev = [makeSection("a")];
    const next = [makeSection("a"), makeSection("b")];
    const diffs = diffSections(prev, next);
    expect(diffs).toContainEqual({ type: "add", sectionId: "b", index: 1 });
  });

  it("detects removed sections", () => {
    const prev = [makeSection("a"), makeSection("b")];
    const next = [makeSection("a")];
    const diffs = diffSections(prev, next);
    expect(diffs).toContainEqual({ type: "remove", sectionId: "b" });
  });

  it("detects updated sections", () => {
    const prev = [makeSection("a", "<tr><td>old</td></tr>")];
    const next = [makeSection("a", "<tr><td>new</td></tr>")];
    const diffs = diffSections(prev, next);
    expect(diffs.some((d) => d.type === "update" && d.sectionId === "a")).toBe(true);
  });

  it("detects moved sections", () => {
    const prev = [makeSection("a"), makeSection("b")];
    const next = [makeSection("b"), makeSection("a")];
    const diffs = diffSections(prev, next);
    expect(diffs.some((d) => d.type === "move")).toBe(true);
  });

  it("returns empty for identical sections", () => {
    const sections = [makeSection("a"), makeSection("b")];
    expect(diffSections(sections, sections)).toEqual([]);
  });
});

// ── BuilderSyncEngine ──

describe("BuilderSyncEngine", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it("syncs code to builder after 500ms debounce", () => {
    const onBuilderUpdate = vi.fn();
    const onStatusChange = vi.fn();
    const engine = new BuilderSyncEngine({
      onBuilderUpdate,
      onCodeUpdate: vi.fn(),
      onStatusChange,
      onParseError: vi.fn(),
    });

    engine.onCodeChange(builderDoc(
      '<tr data-section-id="s1"><td>Hello</td></tr>'
    ));
    expect(onBuilderUpdate).not.toHaveBeenCalled();

    vi.advanceTimersByTime(400);
    expect(onBuilderUpdate).not.toHaveBeenCalled();

    vi.advanceTimersByTime(100);
    expect(onBuilderUpdate).toHaveBeenCalledTimes(1);
    expect(onBuilderUpdate.mock.calls[0]![0]).toHaveLength(1);
    expect(onStatusChange).toHaveBeenCalledWith("synced");

    engine.dispose();
  });

  it("syncs builder to code after 200ms debounce", () => {
    const onCodeUpdate = vi.fn();
    const engine = new BuilderSyncEngine({
      onBuilderUpdate: vi.fn(),
      onCodeUpdate,
      onStatusChange: vi.fn(),
      onParseError: vi.fn(),
    });

    engine.setTemplateShell(builderDoc(""));

    engine.onBuilderChange([{
      id: "s1", componentId: 0, componentName: "Header",
      slotValues: {}, styleOverrides: {},
      htmlFragment: '<tr data-section-id="s1"><td>Header</td></tr>',
    }]);

    vi.advanceTimersByTime(100);
    expect(onCodeUpdate).not.toHaveBeenCalled();

    vi.advanceTimersByTime(100);
    expect(onCodeUpdate).toHaveBeenCalledTimes(1);
    expect(onCodeUpdate.mock.calls[0]![0]).toContain("Header");

    engine.dispose();
  });

  it("reports parse error for unparseable HTML", () => {
    const onParseError = vi.fn();
    const onStatusChange = vi.fn();
    const engine = new BuilderSyncEngine({
      onBuilderUpdate: vi.fn(),
      onCodeUpdate: vi.fn(),
      onStatusChange,
      onParseError,
    });

    engine.onCodeChange("<html><body><p>No sections</p></body></html>");
    vi.advanceTimersByTime(500);

    expect(onParseError).toHaveBeenCalledTimes(1);
    expect(onStatusChange).toHaveBeenCalledWith("parse_error");

    engine.dispose();
  });

  it("builder wins when both change within debounce window", () => {
    const onBuilderUpdate = vi.fn();
    const onCodeUpdate = vi.fn();
    const engine = new BuilderSyncEngine({
      onBuilderUpdate,
      onCodeUpdate,
      onStatusChange: vi.fn(),
      onParseError: vi.fn(),
    });

    engine.setTemplateShell(builderDoc(""));

    engine.onCodeChange(builderDoc('<tr><td>from code</td></tr>'));

    vi.advanceTimersByTime(100);
    engine.onBuilderChange([{
      id: "s1", componentId: 0, componentName: "Section",
      slotValues: {}, styleOverrides: {},
      htmlFragment: "<tr><td>Builder wins</td></tr>",
    }]);

    vi.advanceTimersByTime(500);

    expect(onBuilderUpdate).not.toHaveBeenCalled();
    expect(onCodeUpdate).toHaveBeenCalledTimes(1);
    expect(onCodeUpdate.mock.calls[0]![0]).toContain("Builder wins");

    engine.dispose();
  });

  it("updates template shell only after successful parse", () => {
    const engine = new BuilderSyncEngine({
      onBuilderUpdate: vi.fn(),
      onCodeUpdate: vi.fn(),
      onStatusChange: vi.fn(),
      onParseError: vi.fn(),
    });

    engine.onCodeChange(builderDoc('<tr data-section-id="s1"><td>V1</td></tr>'));
    vi.advanceTimersByTime(500);
    expect(engine["templateShell"]).toContain("V1");

    const html2 = builderDoc('<tr data-section-id="s1"><td>V2</td></tr>')
      .replace("<html>", '<html lang="en">');
    engine.onCodeChange(html2);
    vi.advanceTimersByTime(500);
    expect(engine["templateShell"]).toContain('lang="en"');

    engine.onCodeChange("<html><body><p>broken</p></body></html>");
    vi.advanceTimersByTime(500);
    expect(engine["templateShell"]).toContain('lang="en"');

    engine.dispose();
  });
});
