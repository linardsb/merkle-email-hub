/**
 * Defense-in-depth HTML sanitizer for email template content.
 * Strips dangerous patterns before sending to backend.
 * Preserves MSO conditional comments needed for Outlook.
 */
export function sanitizeHtml(html: string): string {
  let result = html;

  // Strip <script> tags and their content (preserve MSO conditionals)
  result = result.replace(
    /<script\b[^>]*>[\s\S]*?<\/script>/gi,
    ""
  );

  // Strip javascript: protocol in href/src/action attributes
  result = result.replace(
    /(\s(?:href|src|action)\s*=\s*["'])javascript:/gi,
    "$1"
  );

  // Strip on* event handlers (onclick, onload, onerror, etc.)
  result = result.replace(
    /\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi,
    ""
  );

  return result;
}
