/** Convert hex (#RRGGBB) to {r, g, b} 0-255. */
export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const match = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!match || !match[1] || !match[2] || !match[3]) return null;
  return {
    r: parseInt(match[1], 16),
    g: parseInt(match[2], 16),
    b: parseInt(match[3], 16),
  };
}

/** Convert hex to rgb() string. */
export function hexToRgbString(hex: string): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  return `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
}

/** Convert hex to hsl() string. */
export function hexToHslString(hex: string): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  const r = rgb.r / 255,
    g = rgb.g / 255,
    b = rgb.b / 255;
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return `hsl(0, 0%, ${Math.round(l * 100)}%)`;
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else h = ((r - g) / d + 4) / 6;
  return `hsl(${Math.round(h * 360)}, ${Math.round(s * 100)}%, ${Math.round(l * 100)}%)`;
}

/** Euclidean RGB distance between two hex colors. */
export function colorDistance(hex1: string, hex2: string): number {
  const c1 = hexToRgb(hex1),
    c2 = hexToRgb(hex2);
  if (!c1 || !c2) return Infinity;
  return Math.sqrt((c1.r - c2.r) ** 2 + (c1.g - c2.g) ** 2 + (c1.b - c2.b) ** 2);
}

/** Normalize 3-digit hex to 6-digit (e.g. #abc -> #aabbcc). */
function normalizeHex(hex: string): string {
  const h = hex.replace(/^#/, "");
  if (h.length === 3) {
    return `#${h[0]}${h[0]}${h[1]}${h[1]}${h[2]}${h[2]}`;
  }
  return `#${h}`;
}

/**
 * WCAG 2.1 relative luminance (0 = black, 1 = white).
 * Accepts 3-digit or 6-digit hex with optional leading #.
 */
export function relativeLuminance(hex: string): number {
  const rgb = hexToRgb(normalizeHex(hex));
  if (!rgb) return 0;
  const [rs, gs, bs] = [rgb.r / 255, rgb.g / 255, rgb.b / 255].map((c) =>
    c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * rs! + 0.7152 * gs! + 0.0722 * bs!;
}

/** True when the color would be hard to read on a dark (#121212) background. */
export function isDarkColor(hex: string): boolean {
  return relativeLuminance(hex) < 0.3;
}

/** Count occurrences of a hex value in HTML string (case-insensitive). */
export function countHexOccurrences(html: string, hex: string): number {
  const normalized = hex.toLowerCase().replace(/^#/, "");
  // Reject non-hex chars before regex construction so untrusted input cannot
  // inject regex metacharacters (CodeQL detect-non-literal-regexp).
  if (!/^[0-9a-f]{3,8}$/.test(normalized)) return 0;
  const pattern = new RegExp(`#${normalized}`, "gi");
  return (html.match(pattern) || []).length;
}

/**
 * Find all hex colors in HTML that don't match any design token.
 * Returns array of {hex, closestHex, distance}.
 */
export function findOffBrandColors(
  html: string,
  tokenHexes: string[],
): Array<{ hex: string; closestHex: string; distance: number }> {
  if (tokenHexes.length === 0) return [];
  const allHexes = html.match(/#[a-f\d]{6}/gi) || [];
  const unique = [...new Set(allHexes.map((h) => h.toLowerCase()))];
  const tokenSet = new Set(tokenHexes.map((h) => h.toLowerCase()));

  return unique
    .filter((h) => !tokenSet.has(h))
    .map((hex) => {
      let closestHex: string = tokenHexes[0]!;
      let minDist = Infinity;
      for (const t of tokenHexes) {
        const d = colorDistance(hex, t);
        if (d < minDist) {
          minDist = d;
          closestHex = t;
        }
      }
      return { hex, closestHex, distance: minDist };
    });
}

/** Generate CSS custom properties block from token colors and typography. */
export function generateCssVariablesBlock(
  colors: Array<{ name: string; hex: string }>,
  typography: Array<{ name: string; family: string }>,
): string {
  const lines: string[] = [":root {"];
  for (const c of colors) {
    const varName = c.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    lines.push(`  --${varName}: ${c.hex};`);
  }
  for (const t of typography) {
    const varName = t.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    lines.push(`  --font-${varName}: '${t.family}';`);
  }
  lines.push("}");
  return lines.join("\n");
}
