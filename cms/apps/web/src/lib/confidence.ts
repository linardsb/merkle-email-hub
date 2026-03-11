const CONFIDENCE_RE = /<!--\s*CONFIDENCE:\s*([\d.]+)\s*-->/;

/** Extract confidence score (0.0–1.0) from HTML comment, or null if absent/invalid. */
export function extractConfidence(content: string): number | null {
  const match = content.match(CONFIDENCE_RE);
  if (!match?.[1]) return null;
  const val = parseFloat(match[1]);
  return val >= 0 && val <= 1 ? val : null;
}

/** Strip the <!-- CONFIDENCE: X.XX --> comment from content. */
export function stripConfidenceComment(content: string): string {
  return content.replace(CONFIDENCE_RE, "").trim();
}
