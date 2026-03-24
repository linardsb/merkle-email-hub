import DOMPurify from "dompurify";
import type { SectionNode, SectionDiff } from "@/types/visual-builder";

// ── ESP token preservation ──

interface EspTokenMap {
  tokens: Map<string, string>;
  counter: number;
}

/**
 * Extract ESP template tokens into unique placeholders before DOM parsing.
 * Handles: Liquid {% %}, Handlebars {{ }}/{{{ }}}, AMPscript %% %%,
 * ERB/EJS <% %>, SFMC %%[...]%%, and general ESP patterns.
 */
export function extractEspTokens(html: string): { sanitized: string; tokenMap: EspTokenMap } {
  const tokenMap: EspTokenMap = { tokens: new Map(), counter: 0 };

  // Patterns use {0,2000} instead of * to cap backtracking on unclosed delimiters
  const patterns = [
    // Liquid: {% ... %}
    /\{%[\s\S]{0,2000}?%\}/g,
    // Handlebars triple-stache: {{{ ... }}}
    /\{\{\{[\s\S]{0,2000}?\}\}\}/g,
    // Handlebars/Mustache: {{ ... }}
    /\{\{[\s\S]{0,2000}?\}\}/g,
    // AMPscript: %%[...]%% or %%var%%
    /%%\[[\s\S]{0,2000}?\]%%/g,
    /%%[a-zA-Z_][\w.]*%%/g,
    // ERB/EJS: <% ... %>
    /<%[\s\S]{0,2000}?%>/g,
  ];

  let sanitized = html;
  for (const pattern of patterns) {
    sanitized = sanitized.replace(pattern, (match) => {
      const placeholder = `__ESP_${tokenMap.counter}__`;
      tokenMap.tokens.set(placeholder, match);
      tokenMap.counter++;
      return placeholder;
    });
  }

  return { sanitized, tokenMap };
}

/**
 * Restore ESP tokens from placeholders back to original syntax.
 */
export function restoreEspTokens(html: string, tokenMap: EspTokenMap): string {
  let result = html;
  for (const [placeholder, original] of tokenMap.tokens) {
    // Replace all occurrences (DOM may duplicate in some edge cases)
    result = result.split(placeholder).join(original);
  }
  return result;
}

// ── Structural ESP token internalization ──

/**
 * Internalize structural-level ESP conditionals into table cells.
 *
 * ESP templates often wrap entire <tr> rows in conditionals:
 *   {% if user.vip %}<tr><td>VIP Section</td></tr>{% endif %}
 *
 * This is invalid when DOMParser processes the HTML — the browser
 * hoists text nodes out of <table>/<tbody> contexts. This function
 * detects the pattern (after ESP extraction, so tokens are placeholders)
 * and moves the conditional INSIDE the <td> cell:
 *   <tr><td>__ESP_OPEN__ VIP Section __ESP_CLOSE__</td></tr>
 *
 * On export, restoreEspTokens converts placeholders back to original
 * syntax, yielding: <tr><td>{% if user.vip %}VIP Section{% endif %}</td></tr>
 *
 * Supports:
 * - Single-cell rows: open + <tr><td>content</td></tr> + close
 * - Multi-cell rows: open + <tr><td>A</td><td>B</td></tr> + close
 *   (wraps each <td>'s content)
 * - Nested conditionals: open + <tr>...</tr> + else-if + <tr>...</tr> + close
 *   (each branch becomes a row with conditionals inside cells)
 * - Consecutive conditionals: multiple if/endif pairs in sequence
 *
 * Works on placeholder strings (__ESP_N__), not raw ESP syntax.
 */
export function internalizeStructuralEsp(
  html: string,
  tokenMap: EspTokenMap
): string {
  // Build sets for conditional types based on the original token content
  const openTokens = new Set<string>();   // {% if %}, {% unless %}, %%[IF...]%%
  const elseTokens = new Set<string>();   // {% else %}, {% elsif %}, %%[ELSE...]%%
  const closeTokens = new Set<string>();  // {% endif %}, {% endunless %}, %%[ENDIF]%%

  for (const [placeholder, original] of tokenMap.tokens) {
    const trimmed = original.trim();
    if (
      /^\{%[-\s]*(?:if|unless)\b/i.test(trimmed) ||
      /^%%\[?\s*IF\b/i.test(trimmed) ||
      /^<%[-\s]*if\b/i.test(trimmed)
    ) {
      openTokens.add(placeholder);
    } else if (
      /^\{%[-\s]*(?:else|elsif|elseif)\b/i.test(trimmed) ||
      /^%%\[?\s*(?:ELSE|ELSEIF)\b/i.test(trimmed) ||
      /^<%[-\s]*(?:else|elsif)\b/i.test(trimmed)
    ) {
      elseTokens.add(placeholder);
    } else if (
      /^\{%[-\s]*(?:endif|endunless)\b/i.test(trimmed) ||
      /^%%\[?\s*ENDIF\b/i.test(trimmed) ||
      /^<%[-\s]*end\b/i.test(trimmed)
    ) {
      closeTokens.add(placeholder);
    }
  }

  if (openTokens.size === 0) return html;

  // Safety: bail out if too many tokens (prevents quadratic regex alternation)
  if (tokenMap.tokens.size > 200) return html;

  // Build a regex that matches: OPEN_PLACEHOLDER <tr>...</tr> CLOSE_PLACEHOLDER
  // with optional ELSE_PLACEHOLDER <tr>...</tr> branches in between.
  const phAll = [...tokenMap.tokens.keys()].map(escapeRegex).join("|");
  const phOpen = [...openTokens].map(escapeRegex).join("|");
  const phElse = elseTokens.size > 0 ? [...elseTokens].map(escapeRegex).join("|") : null;
  const phClose = [...closeTokens].map(escapeRegex).join("|");

  if (!phOpen || !phClose) return html;

  // Cap <tr> content length to prevent backtracking on large rows
  const trPattern = `<tr\\b[^>]*>[\\s\\S]{0,10000}?</tr>`;
  const elseBranch = phElse
    ? `(?:\\s*(?:${phElse})\\s*${trPattern})*`
    : "";
  const fullPattern = new RegExp(
    `(${phOpen})\\s*(${trPattern})${elseBranch}\\s*(${phClose})`,
    "gi"
  );

  return html.replace(fullPattern, (fullMatch, open: string, ...rest: unknown[]) => {
    // Parse the match to extract branches
    // Simpler approach: find all <tr>...</tr> blocks and their preceding tokens
    const branches: Array<{ token: string | null; trHtml: string }> = [];
    const branchPattern = new RegExp(
      `(?:(${phAll})\\s*)?(${trPattern})`,
      "gi"
    );
    // Skip the open token — it's captured as group 1 of fullPattern
    let branchMatch;
    const innerHtml = fullMatch.slice(open.length);
    // Remove the close token from the end
    const closeMatch = innerHtml.match(new RegExp(`\\s*(${phClose})\\s*$`));
    const close = closeMatch ? closeMatch[1]! : "";
    const middle = closeMatch
      ? innerHtml.slice(0, innerHtml.length - closeMatch[0].length)
      : innerHtml;

    while ((branchMatch = branchPattern.exec(middle)) !== null) {
      const precedingToken = branchMatch[1] ?? null;
      const trHtml = branchMatch[2]!;
      branches.push({ token: precedingToken, trHtml });
    }

    if (branches.length === 0) return fullMatch; // no <tr> found, leave as-is

    // For each branch, internalize the conditional tokens into <td> cells
    const result: string[] = [];
    for (let i = 0; i < branches.length; i++) {
      const branch = branches[i]!;
      const isFirst = i === 0;
      const isLast = i === branches.length - 1;
      const branchOpen = isFirst ? open : (branch.token ?? "");
      const branchClose = isLast ? close : "";

      // Inject tokens inside each <td> in this <tr>
      result.push(injectTokensIntoTr(branch.trHtml, branchOpen, branchClose));
    }

    return result.join("\n");
  });
}

/**
 * Inject ESP placeholder tokens inside each <td> cell of a <tr>.
 * <tr><td>content</td></tr> → <tr><td>OPEN content CLOSE</td></tr>
 */
function injectTokensIntoTr(
  trHtml: string,
  openToken: string,
  closeToken: string
): string {
  if (!openToken && !closeToken) return trHtml;

  // Replace each <td...>content</td> with <td...>OPEN content CLOSE</td>
  // Handle both <td> and <th> for completeness
  return trHtml.replace(
    /(<t[dh]\b[^>]*>)([\s\S]*?)(<\/t[dh]>)/gi,
    (_, tdOpen: string, content: string, tdClose: string) => {
      const prefix = openToken ? `${openToken} ` : "";
      const suffix = closeToken ? ` ${closeToken}` : "";
      return `${tdOpen}${prefix}${content.trim()}${suffix}${tdClose}`;
    }
  );
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// ── CSS parsing ──

/**
 * Parse an inline style string into a property→value map.
 * Handles colons in values (url(), data:, quoted strings) correctly.
 */
export function parseInlineStyle(style: string): Record<string, string> {
  const result: Record<string, string> = {};
  // Split on semicolons that are NOT inside quotes
  const declarations: string[] = [];
  let current = "";
  let inSingle = false;
  let inDouble = false;
  for (let i = 0; i < style.length; i++) {
    const ch = style[i]!;
    if (ch === "'" && !inDouble) inSingle = !inSingle;
    else if (ch === '"' && !inSingle) inDouble = !inDouble;
    else if (ch === ";" && !inSingle && !inDouble) {
      declarations.push(current);
      current = "";
      continue;
    }
    current += ch;
  }
  if (current.trim()) declarations.push(current);

  for (const decl of declarations) {
    // Find the first colon that separates property from value
    const colonIdx = decl.indexOf(":");
    if (colonIdx === -1) continue;
    const prop = decl.slice(0, colonIdx).trim();
    const val = decl.slice(colonIdx + 1).trim();
    if (prop && val && /^[a-zA-Z-]+$/.test(prop)) {
      result[prop] = val;
    }
  }
  return result;
}

// ── DOM helpers ──

/** Tags that are structural, not content — skip when counting children */
const NON_CONTENT_TAGS = new Set([
  "STYLE",
  "SCRIPT",
  "META",
  "LINK",
  "TITLE",
  "HEAD",
]);

function isContentElement(el: Element): boolean {
  return !NON_CONTENT_TAGS.has(el.tagName);
}

/**
 * Detect email "hidden helper" elements (preheader text, tracking pixels)
 * that should not count as content children when finding the content root.
 * These use inline display:none. Responsive-hidden sections use class-based
 * @media hiding and are NOT filtered.
 */
function isHiddenHelperElement(el: Element): boolean {
  const style = el.getAttribute("style") ?? "";
  return /display\s*:\s*none/i.test(style);
}

/**
 * Find the content root — the deepest element whose direct children
 * represent logical email sections.
 *
 * Walks from <body> inward, unwrapping single-child wrapper elements
 * (tables, divs, tds, centers, etc.) until a node with multiple
 * content children is found. For <table> elements, transparently
 * steps into <tbody>.
 *
 * @param requireChildren — when true (default), returns null if no
 *   multi-child node is found. When false, returns the deepest
 *   single-child leaf (used by sectionsToHtml to find insertion point).
 */
export function findContentRoot(
  body: Element,
  requireChildren = true
): Element | null {
  let current: Element = body;
  let deepest: Element = body;
  const MAX_DEPTH = 20;

  for (let depth = 0; depth < MAX_DEPTH; depth++) {
    // For tables, step into tbody transparently
    if (current.tagName === "TABLE") {
      const tbody = current.querySelector(":scope > tbody");
      if (tbody) {
        current = tbody;
        deepest = tbody;
        continue;
      }
    }

    const children = Array.from(current.children).filter(
      (el) => isContentElement(el) && !isHiddenHelperElement(el)
    );

    if (children.length === 0) {
      // No children — return deepest reached if allowed
      return requireChildren ? null : deepest;
    }
    if (children.length === 1) {
      current = children[0]!;
      deepest = current;
      continue;
    }

    // Multiple content children — check if this is a column group
    // If so, keep unwrapping (columns are ONE section, not separate)
    if (isColumnGroup(children)) {
      // This is a column layout — the parent IS the section, don't split
      return current;
    }

    // Multiple content children — this is the content root
    return current;
  }

  return requireChildren ? null : deepest;
}

/**
 * Extract a section name from a preceding HTML comment, if any.
 * Handles both "<!-- section: Name -->" and plain "<!-- Name -->" formats.
 * Skips MSO/IE conditional comments.
 */
function getCommentName(el: Element): string | null {
  let prev: Node | null = el.previousSibling;
  while (prev) {
    if (prev.nodeType === Node.COMMENT_NODE) {
      const text = prev.textContent?.trim() ?? "";
      // Skip MSO/IE conditionals
      if (text.startsWith("[if") || text.startsWith("[endif")) return null;
      if (text.length > 0 && text.length < 100) {
        // Strip "section: " prefix if present
        return text.replace(/^section:\s*/i, "").trim();
      }
    }
    // Stop at previous element — comment must be immediately before this section
    if (prev.nodeType === Node.ELEMENT_NODE) break;
    prev = prev.previousSibling;
  }
  return null;
}

/**
 * Infer a section name from the element's class, id, or tag.
 */
function inferSectionName(el: Element): string {
  const className = (el as HTMLElement).className
    ?.split(/\s+/)
    .find((c) => c.length > 0 && c.length < 30);
  if (className) {
    return className.charAt(0).toUpperCase() + className.slice(1);
  }
  if (el.id && el.id.length < 30) {
    return el.id.charAt(0).toUpperCase() + el.id.slice(1);
  }
  if (el.tagName === "TR") return "Section";
  return el.tagName.charAt(0) + el.tagName.slice(1).toLowerCase();
}

// ── Column group detection ──

/**
 * Dynamically detect whether a set of sibling elements form a column layout.
 * Uses multiple heuristics — works with any HTML structure (tables, divs, etc.).
 */
export function isColumnGroup(children: Element[]): boolean {
  if (children.length < 2 || children.length > 6) return false;

  // Heuristic 1: all share a class name (e.g., "column", "col", "cell")
  const firstClasses = (children[0] as HTMLElement)?.className?.split(/\s+/).filter(Boolean) ?? [];
  if (firstClasses.length > 0) {
    const shared = firstClasses.find((cls) =>
      children.every((el) => (el as HTMLElement).classList?.contains(cls))
    );
    if (shared) return true;
  }

  // Heuristic 2: width attributes sum to ~100%
  const percentWidths = children.map((el) => {
    const w = el.getAttribute("width");
    if (!w) return 0;
    return w.endsWith("%") ? parseFloat(w) : 0;
  }).filter((w) => w > 0);
  if (percentWidths.length === children.length) {
    const sum = percentWidths.reduce((a, b) => a + b, 0);
    if (sum >= 90 && sum <= 105) return true;
  }

  // Heuristic 3: pixel widths that approximately sum to a container width
  const pxWidths = children.map((el) => {
    const w = el.getAttribute("width");
    if (!w) return 0;
    const n = parseFloat(w);
    return !w.endsWith("%") && n > 0 ? n : 0;
  }).filter((w) => w > 0);
  if (pxWidths.length === children.length && pxWidths.length >= 2) {
    const sum = pxWidths.reduce((a, b) => a + b, 0);
    // Common container widths: 600, 640, 580, 560, etc.
    if (sum >= 400 && sum <= 700) return true;
  }

  // Heuristic 4: inline display:inline-block or float:left on all
  const allInline = children.every((el) => {
    const style = el.getAttribute("style") ?? "";
    return /display\s*:\s*inline-?block/i.test(style) || /float\s*:\s*left/i.test(style);
  });
  if (allInline) return true;

  // Heuristic 5: all are <td> elements (columns in a row)
  if (children.every((el) => el.tagName === "TD")) return true;

  // Heuristic 6: all same tag with similar dimensions and same parent is a single <tr>
  const parent = children[0]?.parentElement;
  if (parent?.tagName === "TR" && children.every((el) => el.tagName === "TD")) {
    return true;
  }

  return false;
}

/**
 * Capture non-section content (comments, text nodes, MSO conditionals)
 * preceding an element, for roundtrip preservation.
 */
function capturePrecedingContent(el: Element): string | undefined {
  const parts: string[] = [];
  let prev: Node | null = el.previousSibling;

  // Walk backwards, collect non-element nodes
  const collected: Node[] = [];
  while (prev) {
    if (prev.nodeType === Node.ELEMENT_NODE) break;
    collected.unshift(prev);
    prev = prev.previousSibling;
  }

  for (const node of collected) {
    if (node.nodeType === Node.COMMENT_NODE) {
      parts.push(`<!--${node.textContent ?? ""}-->`);
    } else if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent ?? "";
      if (text.trim()) parts.push(text);
    }
  }

  return parts.length > 0 ? parts.join("") : undefined;
}

// ── Parser ──

/**
 * Parse HTML into a section tree.
 *
 * Strategy 1 (annotated): Elements with `data-section-id` attribute.
 *   Highest fidelity — exact roundtrip with builder/assembler output.
 *
 * Strategy 2 (structural): Find the content root by unwrapping single-child
 *   wrappers from <body> inward. The content root's direct children become
 *   sections. Works with any HTML structure — tables, divs, columns, etc.
 *   Uses preceding HTML comments for section names when available.
 *   Detects column layouts dynamically and groups them as a single section.
 *
 * ESP template tokens ({% %}, {{ }}, %%, <% %>) are preserved through
 * extraction/restoration to prevent DOMParser from mangling them.
 *
 * Returns null if HTML cannot be parsed into sections.
 */
export function htmlToSections(html: string): SectionNode[] | null {
  // Extract ESP tokens before DOM parsing
  const { sanitized: extracted, tokenMap } = extractEspTokens(html);

  // Internalize structural-level ESP conditionals into <td> cells.
  // e.g. {% if vip %}<tr><td>VIP</td></tr>{% endif %}
  //    → <tr><td>{% if vip %} VIP {% endif %}</td></tr>
  const sanitized = internalizeStructuralEsp(extracted, tokenMap);

  const parser = new DOMParser();
  const doc = parser.parseFromString(sanitized, "text/html");

  // Strategy 1: data-section-id attributes (highest fidelity)
  const annotated = doc.querySelectorAll("[data-section-id]");
  if (annotated.length > 0) {
    const sections: SectionNode[] = [];
    for (const el of annotated) {
      const id = el.getAttribute("data-section-id") ?? crypto.randomUUID();
      const componentId = parseInt(
        el.getAttribute("data-component-id") ?? "0",
        10
      );
      const componentName =
        el.getAttribute("data-component-name") ?? "Section";

      const slotValues: Record<string, string> = {};
      for (const slotEl of el.querySelectorAll("[data-slot-name]")) {
        const slotName = slotEl.getAttribute("data-slot-name");
        if (slotName)
          slotValues[slotName] = DOMPurify.sanitize(slotEl.innerHTML);
      }

      const styleOverrides = parseInlineStyle(
        el.getAttribute("style") ?? ""
      );

      const precedingContent = capturePrecedingContent(el);
      const fragment = restoreEspTokens((el as HTMLElement).outerHTML, tokenMap);

      sections.push({
        id,
        componentId: isNaN(componentId) ? 0 : componentId,
        componentName,
        slotValues,
        styleOverrides,
        htmlFragment: fragment,
        precedingContent: precedingContent
          ? restoreEspTokens(precedingContent, tokenMap)
          : undefined,
      });
    }
    return sections;
  }

  // Strategy 2: Structural analysis — find content root, children = sections
  const contentRoot = findContentRoot(doc.body);
  if (!contentRoot) return null;

  const children = Array.from(contentRoot.children).filter(isContentElement);
  if (children.length === 0) return null;

  // Check if all children form a column group — treat as single section
  if (isColumnGroup(children)) {
    const parentName = inferSectionName(contentRoot);
    const name = parentName === "Section" || parentName === "Tbody"
      ? "Columns"
      : parentName;
    const fragment = restoreEspTokens(
      (contentRoot as HTMLElement).innerHTML,
      tokenMap
    );
    return [{
      id: crypto.randomUUID(),
      componentId: 0,
      componentName: name,
      slotValues: {},
      styleOverrides: {},
      htmlFragment: fragment,
    }];
  }

  const sections: SectionNode[] = [];
  for (const child of children) {
    const commentName = getCommentName(child);
    const name = commentName ?? inferSectionName(child);

    // Check if this child's own children form a column group
    const grandchildren = Array.from(child.children).filter(isContentElement);
    let fragment: string;
    if (grandchildren.length >= 2 && isColumnGroup(grandchildren)) {
      // Group columns as a single section — use the parent element
      fragment = restoreEspTokens((child as HTMLElement).outerHTML, tokenMap);
    } else {
      fragment = restoreEspTokens((child as HTMLElement).outerHTML, tokenMap);
    }

    const precedingContent = capturePrecedingContent(child);

    sections.push({
      id: crypto.randomUUID(),
      componentId: 0,
      componentName: name,
      slotValues: {},
      styleOverrides: {},
      htmlFragment: fragment,
      precedingContent: precedingContent
        ? restoreEspTokens(precedingContent, tokenMap)
        : undefined,
    });
  }

  return sections.length > 0 ? sections : null;
}

// ── Serializer ──

/**
 * Serialize section tree back to HTML.
 *
 * Uses DOM parsing to find the content root in the template shell,
 * replaces its children with the new section fragments, then
 * serializes back. Preserves doctype and document structure.
 * Emits precedingContent (comments, text) before each section.
 */
export function sectionsToHtml(
  sections: SectionNode[],
  templateShell: string
): string {
  // Build a unified token map: extract ESP tokens from ALL sources using
  // a shared counter so placeholders are unique across shell + all sections.
  const unifiedMap: EspTokenMap = { tokens: new Map(), counter: 0 };

  function extractUnified(html: string): string {
    const patterns = [
      /\{%[\s\S]*?%\}/g,
      /\{\{\{[\s\S]*?\}\}\}/g,
      /\{\{[\s\S]*?\}\}/g,
      /%%\[[\s\S]*?\]%%/g,
      /%%[a-zA-Z_][\w.]*%%/g,
      /<%[\s\S]*?%>/g,
    ];
    let sanitized = html;
    for (const pattern of patterns) {
      sanitized = sanitized.replace(pattern, (match) => {
        const placeholder = `__ESP_${unifiedMap.counter}__`;
        unifiedMap.tokens.set(placeholder, match);
        unifiedMap.counter++;
        return placeholder;
      });
    }
    return sanitized;
  }

  const sanitizedShell = extractUnified(templateShell);

  const parser = new DOMParser();
  const doc = parser.parseFromString(sanitizedShell, "text/html");

  // requireChildren=false so we find the insertion point even in empty shells
  const contentRoot = findContentRoot(doc.body, false);
  if (!contentRoot) return templateShell;

  // Remove existing content children (preserve non-content like <style>)
  const existing = Array.from(contentRoot.children).filter(isContentElement);
  for (const child of existing) child.remove();

  // Also remove text/comment nodes between content children
  const nodesToRemove: ChildNode[] = [];
  for (const node of Array.from(contentRoot.childNodes)) {
    if (node.nodeType === Node.TEXT_NODE || node.nodeType === Node.COMMENT_NODE) {
      nodesToRemove.push(node as ChildNode);
    }
  }
  for (const node of nodesToRemove) node.remove();

  // Insert new section fragments using a context-appropriate container.
  const isTableContext =
    contentRoot.tagName === "TBODY" ||
    contentRoot.tagName === "TABLE" ||
    contentRoot.tagName === "THEAD" ||
    contentRoot.tagName === "TFOOT";

  for (const section of sections) {
    // Emit preceding content (comments, text) before the section
    if (section.precedingContent) {
      const sanitizedPreceding = extractUnified(section.precedingContent);
      const tempDiv = doc.createElement("div");
      tempDiv.innerHTML = sanitizedPreceding;
      while (tempDiv.firstChild) {
        contentRoot.appendChild(tempDiv.firstChild);
      }
    }

    const sanitizedFragment = extractUnified(section.htmlFragment);

    if (isTableContext) {
      const tempTable = doc.createElement("table");
      const tempTbody = doc.createElement("tbody");
      tempTable.appendChild(tempTbody);
      tempTbody.innerHTML = sanitizedFragment;
      while (tempTbody.firstChild) {
        contentRoot.appendChild(tempTbody.firstChild);
      }
    } else {
      const temp = doc.createElement("div");
      temp.innerHTML = sanitizedFragment;
      while (temp.firstChild) {
        contentRoot.appendChild(temp.firstChild);
      }
    }
  }

  // Reconstruct with original doctype using DOM doctype node
  let doctypeStr = "";
  if (doc.doctype) {
    const dt = doc.doctype;
    doctypeStr = `<!DOCTYPE ${dt.name}${dt.publicId ? ` PUBLIC "${dt.publicId}"` : ""}${dt.systemId ? ` "${dt.systemId}"` : ""}>`;
  } else {
    const match = templateShell.match(/<!DOCTYPE[^>]*>/i);
    if (match) doctypeStr = match[0];
  }

  const prefix = doctypeStr ? doctypeStr + "\n" : "";
  let result = prefix + doc.documentElement.outerHTML;

  // Restore all ESP tokens from the unified map
  result = restoreEspTokens(result, unifiedMap);

  return result;
}

// ── Diff ──

/**
 * Compute minimal diff between two section arrays.
 */
export function diffSections(
  prev: SectionNode[],
  next: SectionNode[]
): SectionDiff[] {
  const diffs: SectionDiff[] = [];
  const nextIds = new Set(next.map((s) => s.id));

  const prevById = new Map<string, SectionNode>();
  const prevIndexById = new Map<string, number>();
  for (let i = 0; i < prev.length; i++) {
    const s = prev[i]!;
    prevById.set(s.id, s);
    prevIndexById.set(s.id, i);
  }

  for (const s of prev) {
    if (!nextIds.has(s.id)) {
      diffs.push({ type: "remove", sectionId: s.id });
    }
  }

  for (let i = 0; i < next.length; i++) {
    const s = next[i]!;
    const prevSection = prevById.get(s.id);
    if (!prevSection) {
      diffs.push({ type: "add", sectionId: s.id, index: i });
    } else {
      if (prevSection.htmlFragment !== s.htmlFragment) {
        diffs.push({ type: "update", sectionId: s.id, updates: s });
      }
      const prevIdx = prevIndexById.get(s.id)!;
      if (prevIdx !== i) {
        diffs.push({ type: "move", sectionId: s.id, index: i });
      }
    }
  }

  return diffs;
}
