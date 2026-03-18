/**
 * HTML annotation utilities for builder <-> code roundtrip fidelity.
 * data-section-id and data-slot-name attributes are invisible in rendered output.
 */

/** Strip builder annotations from HTML for export/render */
export function stripAnnotations(html: string): string {
  return html
    .replace(/\s+data-section-id="[^"]*"/g, "")
    .replace(/\s+data-section-id='[^']*'/g, "")
    .replace(/\s+data-slot-name="[^"]*"/g, "")
    .replace(/\s+data-slot-name='[^']*'/g, "")
    .replace(/\s+data-component-id="[^"]*"/g, "")
    .replace(/\s+data-component-id='[^']*'/g, "")
    .replace(/\s+data-component-name="[^"]*"/g, "")
    .replace(/\s+data-component-name='[^']*'/g, "");
}

/** Check if HTML has builder section annotations */
export function hasAnnotations(html: string): boolean {
  return /data-section-id="[^"]*"/.test(html) || /data-section-id='[^']*'/.test(html);
}
