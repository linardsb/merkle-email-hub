import { describe, expect, it } from "vitest";
import { ensureDarkModeContrast } from "../dark-mode-contrast";

describe("ensureDarkModeContrast", () => {
  it("replaces dark inline colors with light fallback", () => {
    const input = `<td style="color:#101828; font-size:14px">Nav link</td>`;
    const result = ensureDarkModeContrast(input);
    expect(result).toContain("color: #e5e5e5 !important");
    expect(result).not.toContain("#101828");
  });

  it("preserves light inline colors", () => {
    const input = `<td style="color:#ffffff; font-size:14px">White text</td>`;
    const result = ensureDarkModeContrast(input);
    expect(result).toContain("#ffffff");
    expect(result).not.toContain("!important");
  });

  it("handles 3-digit hex colors", () => {
    const input = `<td style="color:#111">Dark</td>`;
    const result = ensureDarkModeContrast(input);
    expect(result).toContain("#e5e5e5 !important");
  });

  it("handles multiple color declarations", () => {
    const input = `
      <td style="color:#101828">Dark nav</td>
      <td style="color:#e5e5e5">Light text</td>
      <a style="color:#0f172a">Dark link</a>
    `;
    const result = ensureDarkModeContrast(input);
    expect(result).not.toContain("#101828");
    expect(result).not.toContain("#0f172a");
    expect(result).toContain("#e5e5e5"); // original light text preserved
  });

  it("does not modify HTML without inline color styles", () => {
    const input = `<td class="nav-link">Plain</td>`;
    const result = ensureDarkModeContrast(input);
    expect(result).toBe(input);
  });

  it("preserves other style properties", () => {
    const input = `<td style="font-size:14px; color:#101828; padding:10px">Text</td>`;
    const result = ensureDarkModeContrast(input);
    expect(result).toContain("font-size:14px");
    expect(result).toContain("padding:10px");
  });

  it("does not replace background-color", () => {
    const input = `<td style="background-color:#1a1a2e; color:#101828">Text</td>`;
    const result = ensureDarkModeContrast(input);
    expect(result).toContain("background-color:#1a1a2e");
    expect(result).not.toContain("#101828");
    expect(result).toContain("#e5e5e5 !important");
  });

  it("does not replace border-color", () => {
    const input = `<td style="border-color:#222222">Text</td>`;
    const result = ensureDarkModeContrast(input);
    expect(result).toContain("border-color:#222222");
  });
});
