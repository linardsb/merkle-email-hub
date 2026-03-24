/**
 * Detect pre-compiled email HTML that should bypass Maizzle's render() pipeline.
 * All 4 heuristics must pass for passthrough to activate.
 */
export function isPreCompiledEmail(source) {
  // 1. No Maizzle template syntax
  const MAIZZLE_TAGS = /<(extends|block|component|x-[a-z]|fetch|outlook)\b/i;
  if (MAIZZLE_TAGS.test(source)) return false;

  // 2. Has inline styles (≥3 elements with style="...")
  const inlineStyleCount = (source.match(/\sstyle\s*=\s*"/gi) || []).length;
  if (inlineStyleCount < 3) return false;

  // 3. Has table-based layout (≥2 tables with presentation role or layout attrs)
  const TABLE_LAYOUT = /<table\b[^>]*(?:role\s*=\s*"presentation"|cellpadding|cellspacing|width\s*=|align\s*=)[^>]*>/gi;
  const tableCount = (source.match(TABLE_LAYOUT) || []).length;
  if (tableCount < 2) return false;

  // 4. Has document shell (DOCTYPE or html+body)
  const hasDoctype = /<!DOCTYPE/i.test(source);
  const hasHtmlBody = /<html\b/i.test(source) && /<body\b/i.test(source);
  if (!hasDoctype && !hasHtmlBody) return false;

  return true;
}
