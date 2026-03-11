/**
 * Extract component slugs from editor HTML.
 * Matches `<component src="components/slug">` and `<component src="slug">` patterns.
 */
export function detectComponentRefs(html: string): string[] {
  const pattern =
    /<component\s+[^>]*src=["'](?:components\/)?([^"']+)["'][^>]*>/gi;
  const slugs = new Set<string>();
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(html)) !== null) {
    const slug = match[1];
    if (slug) slugs.add(slug);
  }
  return Array.from(slugs);
}
