/**
 * Defense-in-depth HTML sanitizer for email template content.
 * Strips dangerous patterns before sending to backend.
 * Preserves MSO conditional comments needed for Outlook.
 */
export function sanitizeHtml(html: string): string {
  let result = html;

  // Strip <script> tags and their content (preserve MSO conditionals).
  // Closing tag accepts any chars until `>` (not just whitespace) to match
  // browser-tolerant variants like `</script\t\n bar>` (CodeQL js/bad-tag-filter).
  let prevScript;
  do {
    prevScript = result;
    result = result.replace(
      /<script\b[^>]*>[\s\S]*?<\/script\b[^>]*>/gi,
      ""
    );
  } while (result !== prevScript);

  // Strip javascript: protocol in href/src/action attributes
  result = result.replace(
    /(\s(?:href|src|action)\s*=\s*["'])javascript:/gi,
    "$1"
  );

  // Strip on* event handlers (onclick, onload, onerror, etc.)
  // Loop until stable to prevent incomplete sanitization (CodeQL js/incomplete-multi-character-sanitization)
  let prev;
  do {
    prev = result;
    result = result.replace(
      /\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi,
      ""
    );
  } while (result !== prev);

  return result;
}
