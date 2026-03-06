import { describe, it, expect } from "vitest";
import { sanitizeHtml } from "./sanitize-html";

describe("sanitizeHtml", () => {
  it("strips script tags", () => {
    const input = '<div>Hello</div><script>alert("xss")</script>';
    expect(sanitizeHtml(input)).toBe("<div>Hello</div>");
  });

  it("strips javascript: protocol from href", () => {
    const input = '<a href="javascript:alert(1)">click</a>';
    expect(sanitizeHtml(input)).toBe('<a href="alert(1)">click</a>');
  });

  it("strips on* event handlers", () => {
    const input = '<img src="img.png" onerror="alert(1)">';
    expect(sanitizeHtml(input)).toBe('<img src="img.png">');
  });

  it("strips nested on* handlers that form after first pass", () => {
    const input = '<img src="x" ononerror="alert(1)"error="alert(2)">';
    const result = sanitizeHtml(input);
    expect(result).not.toMatch(/on[a-z]+\s*=/i);
  });

  it("preserves MSO conditional comments", () => {
    const input = "<!--[if mso]><v:rect><![endif]-->";
    expect(sanitizeHtml(input)).toBe(input);
  });

  it("preserves clean HTML", () => {
    const input = '<table role="presentation"><tr><td>Content</td></tr></table>';
    expect(sanitizeHtml(input)).toBe(input);
  });
});
