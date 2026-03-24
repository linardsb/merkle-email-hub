import { isDarkColor } from "./color-utils";

const DARK_FALLBACK_TEXT = "#e5e5e5";

/**
 * When dark mode preview is active, replace dark inline text colors with
 * readable light alternatives. Only touches color declarations in style
 * attributes. Operates on already-sanitised compiled HTML.
 */
export function ensureDarkModeContrast(html: string): string {
  return html.replace(
    /style="([^"]*?)(?<![a-zA-Z-])color:\s*#([0-9a-fA-F]{3,6})([^"]*)"/gi,
    (match, pre: string, hex: string, post: string) => {
      if (!isDarkColor(hex)) return match;
      return `style="${pre}color: ${DARK_FALLBACK_TEXT} !important${post}"`;
    },
  );
}
