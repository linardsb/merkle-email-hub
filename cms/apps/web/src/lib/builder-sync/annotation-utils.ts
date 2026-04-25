/**
 * Annotation manipulation helpers for section refinement operations.
 * Used by the section-refinement-toolbar to merge, split, unwrap, and rename sections.
 */

/**
 * Merge adjacent sections: remove inner data-section-id attributes, keep the first.
 * The merged section takes the first section's ID and component name.
 */
export function mergeSections(html: string, sectionIds: string[]): string {
  if (sectionIds.length < 2) return html;

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  // Keep the first section's annotation, remove the rest
  for (let i = 1; i < sectionIds.length; i++) {
    const el = doc.querySelector(`[data-section-id="${sectionIds[i]}"]`);
    if (el) {
      el.removeAttribute("data-section-id");
      el.removeAttribute("data-component-name");
      el.removeAttribute("data-section-layout");
    }
  }

  return doc.documentElement.outerHTML;
}

/**
 * Split a section at a given child index: the children before splitIndex stay
 * with the original section, children at and after splitIndex get a new section ID.
 */
export function splitSection(html: string, sectionId: string, splitIndex: number): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  const section = doc.querySelector(`[data-section-id="${sectionId}"]`);
  if (!section) return html;

  const children = Array.from(section.children);
  if (splitIndex <= 0 || splitIndex >= children.length) return html;

  // Create a wrapper for the second half
  const newSection = doc.createElement(section.tagName.toLowerCase());
  const newId = crypto.randomUUID();
  newSection.setAttribute("data-section-id", newId);
  newSection.setAttribute("data-component-name", "Content");

  // Copy relevant attributes from original
  for (const attr of Array.from(section.attributes)) {
    if (
      attr.name !== "data-section-id" &&
      attr.name !== "data-component-name" &&
      attr.name !== "data-section-layout"
    ) {
      newSection.setAttribute(attr.name, attr.value);
    }
  }

  // Move children at and after splitIndex to the new section
  const childrenToMove = children.slice(splitIndex);
  for (const child of childrenToMove) {
    newSection.appendChild(child);
  }

  // Insert new section after the original
  section.after(newSection);

  return doc.documentElement.outerHTML;
}

/**
 * Unwrap a section: remove its data-section-id so children merge into the parent flow.
 */
export function unwrapSection(html: string, sectionId: string): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  const el = doc.querySelector(`[data-section-id="${sectionId}"]`);
  if (el) {
    el.removeAttribute("data-section-id");
    el.removeAttribute("data-component-name");
    el.removeAttribute("data-section-layout");
  }

  return doc.documentElement.outerHTML;
}

/**
 * Rename a section's component name.
 */
export function renameSection(html: string, sectionId: string, newName: string): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  const el = doc.querySelector(`[data-section-id="${sectionId}"]`);
  if (el) {
    el.setAttribute("data-component-name", newName);
  }

  return doc.documentElement.outerHTML;
}
