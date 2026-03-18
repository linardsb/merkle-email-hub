"use client";

import { useReducer, useCallback, useMemo } from "react";
import DOMPurify from "dompurify";
import type {
  BuilderSection,
  BuilderState,
  BuilderAction,
  HistoryEntry,
} from "@/types/visual-builder";
import { DEFAULT_RESPONSIVE, DEFAULT_ADVANCED } from "@/types/visual-builder";
import { findContentRoot } from "@/lib/builder-sync/ast-mapper";

const MAX_HISTORY = 50;

function pushHistory(state: BuilderState): HistoryEntry[] {
  const newHistory = state.history.slice(0, state.historyIndex + 1);
  newHistory.push({
    sections: structuredClone(state.sections),
    timestamp: Date.now(),
  });
  if (newHistory.length > MAX_HISTORY) newHistory.shift();
  return newHistory;
}

function builderReducer(
  state: BuilderState,
  action: BuilderAction
): BuilderState {
  switch (action.type) {
    case "ADD_SECTION": {
      const history = pushHistory(state);
      const sections = [...state.sections];
      const idx = action.atIndex ?? sections.length;
      sections.splice(idx, 0, action.section);
      return {
        ...state,
        sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "REMOVE_SECTION": {
      const history = pushHistory(state);
      const sections = state.sections.filter(
        (s) => s.id !== action.sectionId
      );
      const selectedSectionId =
        state.selectedSectionId === action.sectionId
          ? null
          : state.selectedSectionId;
      return {
        ...state,
        sections,
        selectedSectionId,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "DUPLICATE_SECTION": {
      const history = pushHistory(state);
      const idx = state.sections.findIndex(
        (s) => s.id === action.sectionId
      );
      if (idx === -1) return state;
      const original = state.sections[idx]!;
      const cloned = structuredClone(original);
      const duplicate: BuilderSection = {
        ...cloned,
        id: crypto.randomUUID(),
      };
      const sections = [...state.sections];
      sections.splice(idx + 1, 0, duplicate);
      return {
        ...state,
        sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "MOVE_SECTION": {
      if (action.fromIndex < 0 || action.fromIndex >= state.sections.length) return state;
      const history = pushHistory(state);
      const sections = [...state.sections];
      const [moved] = sections.splice(action.fromIndex, 1) as [BuilderSection];
      sections.splice(action.toIndex, 0, moved);
      return {
        ...state,
        sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "UPDATE_SECTION": {
      const history = pushHistory(state);
      const sections = state.sections.map((s) =>
        s.id === action.sectionId ? { ...s, ...action.updates } : s
      );
      return {
        ...state,
        sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "SELECT_SECTION":
      return { ...state, selectedSectionId: action.sectionId };
    case "SET_SECTIONS": {
      const history = pushHistory(state);
      return {
        ...state,
        sections: action.sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "UNDO": {
      if (state.historyIndex <= 0) return state;
      const newIndex = state.historyIndex - 1;
      return {
        ...state,
        sections: structuredClone(state.history[newIndex]!.sections),
        historyIndex: newIndex,
      };
    }
    case "REDO": {
      if (state.historyIndex >= state.history.length - 1) return state;
      const newIndex = state.historyIndex + 1;
      return {
        ...state,
        sections: structuredClone(state.history[newIndex]!.sections),
        historyIndex: newIndex,
      };
    }
    default:
      return state;
  }
}

const INITIAL_STATE: BuilderState = {
  sections: [],
  selectedSectionId: null,
  history: [{ sections: [], timestamp: Date.now() }],
  historyIndex: 0,
};

export function useBuilderState() {
  const [state, dispatch] = useReducer(builderReducer, INITIAL_STATE);

  const addSection = useCallback(
    (section: BuilderSection, atIndex?: number) =>
      dispatch({ type: "ADD_SECTION", section, atIndex }),
    []
  );
  const removeSection = useCallback(
    (sectionId: string) =>
      dispatch({ type: "REMOVE_SECTION", sectionId }),
    []
  );
  const duplicateSection = useCallback(
    (sectionId: string) =>
      dispatch({ type: "DUPLICATE_SECTION", sectionId }),
    []
  );
  const moveSection = useCallback(
    (fromIndex: number, toIndex: number) =>
      dispatch({ type: "MOVE_SECTION", fromIndex, toIndex }),
    []
  );
  const updateSection = useCallback(
    (sectionId: string, updates: Partial<BuilderSection>) =>
      dispatch({ type: "UPDATE_SECTION", sectionId, updates }),
    []
  );
  const selectSection = useCallback(
    (sectionId: string | null) =>
      dispatch({ type: "SELECT_SECTION", sectionId }),
    []
  );
  const setSections = useCallback(
    (sections: BuilderSection[]) =>
      dispatch({ type: "SET_SECTIONS", sections }),
    []
  );
  const undo = useCallback(() => dispatch({ type: "UNDO" }), []);
  const redo = useCallback(() => dispatch({ type: "REDO" }), []);

  const canUndo = state.historyIndex > 0;
  const canRedo = state.historyIndex < state.history.length - 1;

  return {
    ...state,
    addSection,
    removeSection,
    duplicateSection,
    moveSection,
    updateSection,
    selectSection,
    setSections,
    undo,
    redo,
    canUndo,
    canRedo,
  };
}

// ── Sanitization ──

/**
 * Sanitize a CSS value — strip injection vectors.
 * Preserves quotes and commas for legitimate CSS values like font-family.
 */
function sanitizeCssValue(value: string): string {
  return value
    .replace(/expression\s*\(/gi, "")
    .replace(/behavior\s*:/gi, "")
    .replace(/url\s*\([^)]*(?:javascript|vbscript|data\s*:\s*text\/html)[^)]*\)/gi, "")
    .replace(/<|>/g, "");
}

/**
 * Sanitize a CSS property name — only allow valid CSS property characters.
 */
function sanitizeCssProperty(prop: string): string {
  return prop.replace(/[^a-zA-Z0-9-]/g, "");
}

/**
 * Check if a URI is safe (not a script/data injection vector).
 */
function isSafeUri(uri: string): boolean {
  const trimmed = uri.trim().toLowerCase();
  if (/^(javascript|vbscript|data\s*:\s*text\/html):/i.test(trimmed)) return false;
  return true;
}

/**
 * Sanitize a CSS selector value (section ID) to prevent selector injection.
 */
function sanitizeSelectorValue(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "");
}

// ── Token override system ──

/** Dynamic token→CSS property mapping (Bug 4 fix) */
const TOKEN_CSS_MAP: Record<string, string> = {
  background: "background-color",
  font: "font-family",
  font_size: "font-size",
  text_align: "text-align",
  color: "color",
  line_height: "line-height",
  letter_spacing: "letter-spacing",
  border: "border",
  width: "width",
  spacing_top: "padding-top",
  spacing_right: "padding-right",
  spacing_bottom: "padding-bottom",
  spacing_left: "padding-left",
};

/**
 * Build inline style string from token overrides using dynamic mapping.
 */
function buildTokenStyles(tokens: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const [tokenKey, cssProperty] of Object.entries(TOKEN_CSS_MAP)) {
    const value = tokens[tokenKey];
    if (typeof value === "string" && value) {
      parts.push(`${cssProperty}:${sanitizeCssValue(value)}`);
    }
  }
  return parts.join(";");
}

// ── Section processing (structure-preserving) ──

/**
 * Process a single section's HTML: apply slot fills, token overrides,
 * HTML attributes, CSS class, and builder annotations.
 * Preserves the section's original HTML structure — no re-wrapping.
 */
function processSection(section: BuilderSection): string {
  const temp = document.createElement("div");
  temp.innerHTML = section.html;
  const root = temp.firstElementChild;
  if (!root) return section.html;

  // 1. Add builder annotations
  root.setAttribute("data-section-id", section.id);
  if (section.componentId) {
    root.setAttribute("data-component-id", String(section.componentId));
    root.setAttribute("data-component-name", section.componentName);
  }

  // 2. Apply slot fills
  for (const slotDef of section.slotDefinitions) {
    const fill = section.slotFills[slotDef.slot_id];
    if (fill && slotDef.selector) {
      const slotEl = root.querySelector(slotDef.selector);
      if (slotEl) {
        slotEl.setAttribute("data-slot-name", slotDef.slot_id);
        if (slotDef.slot_type === "cta") {
          try {
            const { text, url } = JSON.parse(fill) as { text: string; url: string };
            slotEl.textContent = text;
            if (slotEl.tagName === "A" && isSafeUri(url)) {
              slotEl.setAttribute("href", url);
            }
          } catch {
            slotEl.innerHTML = DOMPurify.sanitize(fill);
          }
        } else if (slotDef.slot_type === "image") {
          try {
            const { src, alt } = JSON.parse(fill) as { src: string; alt: string };
            if (isSafeUri(src)) slotEl.setAttribute("src", src);
            slotEl.setAttribute("alt", alt ?? "");
          } catch { /* leave as-is */ }
        } else {
          slotEl.innerHTML = DOMPurify.sanitize(fill);
        }
      }
    }
  }

  // 3. Merge token override styles (additive, not replacing)
  const tokenStyles = buildTokenStyles(section.tokenOverrides);
  if (tokenStyles) {
    const existing = root.getAttribute("style") ?? "";
    root.setAttribute(
      "style",
      existing ? `${existing};${tokenStyles}` : tokenStyles
    );
  }

  // 4. Apply HTML attributes from AdvancedConfig (with security validation)
  for (const [key, val] of Object.entries(section.advanced.htmlAttributes)) {
    // Block event handlers and style (style handled via tokens)
    if (/^on/i.test(key) || key === "style") continue;
    // Block dangerous URI schemes
    if (/^(javascript|data|vbscript):/i.test(val)) continue;
    root.setAttribute(key, val);
  }

  // 5. Apply custom CSS class (add to existing classes, don't replace)
  if (section.advanced.customCssClass) {
    const safeClass = section.advanced.customCssClass.replace(
      /[^a-zA-Z0-9_\-\s]/g,
      ""
    );
    if (safeClass) {
      root.classList.add(
        ...safeClass.split(/\s+/).filter(Boolean)
      );
    }
  }

  return root.outerHTML;
}

// ── Responsive CSS generation ──

/**
 * Build responsive CSS for sections that have mobile overrides.
 */
function buildResponsiveCss(sections: BuilderSection[]): string {
  const rules: string[] = [];
  for (const s of sections) {
    const r = s.responsive;
    const safeId = sanitizeSelectorValue(s.id);
    const sel = `[data-section-id="${safeId}"]`;

    if (r.stackOnMobile) {
      rules.push(`@media (max-width:480px) { ${sel} td { display:block !important; width:100% !important; } }`);
      rules.push(`@media (max-width:480px) { ${sel} table { width:100% !important; } }`);
    }
    if (r.fullWidthImageOnMobile) {
      rules.push(`@media (max-width:480px) { ${sel} img { width:100% !important; height:auto !important; } }`);
    }
    if (r.mobileFontSize) {
      const safeFontSize = sanitizeCssValue(r.mobileFontSize);
      rules.push(`@media (max-width:480px) { ${sel} { font-size:${safeFontSize} !important; } }`);
    }
    if (r.mobileHide) {
      rules.push(`@media (max-width:480px) { ${sel} { display:none !important; } }`);
    }
    if (r.mobilePaddingOverride) {
      const safePadding = sanitizeCssValue(r.mobilePaddingOverride);
      rules.push(`@media (max-width:480px) { ${sel} { padding:${safePadding} !important; } }`);
    }
    if (r.mobileTextAlign) {
      const safeAlign = sanitizeCssValue(r.mobileTextAlign);
      rules.push(`@media (max-width:480px) { ${sel} { text-align:${safeAlign} !important; } }`);
    }
  }
  return rules.length > 0 ? `<style>${rules.join("\n")}</style>` : "";
}

// ── Dark mode CSS generation ──

/**
 * Build dark mode CSS from section overrides.
 * Generates both @media (prefers-color-scheme:dark) and [data-ogsc] rules
 * for broad client support (Apple Mail, Outlook app, etc.).
 */
function buildDarkModeCss(sections: BuilderSection[]): string {
  const rules: string[] = [];
  for (const s of sections) {
    const entries = Object.entries(s.advanced.darkModeOverrides);
    if (entries.length === 0) continue;
    const safeId = sanitizeSelectorValue(s.id);
    const decls = entries
      .map(([prop, val]) => `${sanitizeCssProperty(prop)}:${sanitizeCssValue(val)}`)
      .join(";");
    rules.push(
      `@media (prefers-color-scheme:dark) { [data-section-id="${safeId}"] { ${decls} } }`
    );
    // Outlook app targeting
    rules.push(
      `[data-ogsc] [data-section-id="${safeId}"] { ${decls} }`
    );
  }
  return rules.length > 0 ? `<style>${rules.join("\n")}</style>` : "";
}

// ── MSO conditional wrapping ──

/**
 * Wrap content with ghost table pattern for Outlook.
 * Does NOT hide content from non-Outlook — provides table structure for Outlook
 * while modern clients see the div/content directly.
 */
function wrapMsoGhostTable(html: string): string {
  return `<!--[if mso]><table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td><![endif]-->\n${html}\n<!--[if mso]></td></tr></table><![endif]-->`;
}

// ── Document assembly ──

/**
 * Assemble processed sections into a complete email HTML document.
 *
 * With templateShell: injects sections into the shell's content root,
 * preserving original document structure (doctype, head, body wrapper).
 *
 * Without templateShell: uses a standard email shell, but each section
 * preserves its own HTML structure — NO re-wrapping in <tr><td>.
 */
function assembleDocument(
  processedSections: string[],
  sectionNames: string[],
  headStyles: string,
  templateShell?: string
): string {
  if (templateShell) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(templateShell, "text/html");
    const contentRoot = findContentRoot(doc.body, false);
    if (contentRoot) {
      // Remove existing content children
      const existingContent = Array.from(contentRoot.children).filter(
        (el) => !["STYLE", "SCRIPT", "META", "LINK"].includes(el.tagName)
      );
      for (const child of existingContent) child.remove();

      // Remove text/comment nodes between sections
      const textNodes: ChildNode[] = [];
      for (const node of Array.from(contentRoot.childNodes)) {
        if (node.nodeType === Node.TEXT_NODE || node.nodeType === Node.COMMENT_NODE) {
          textNodes.push(node as ChildNode);
        }
      }
      for (const node of textNodes) node.remove();

      // Determine if content root is a table context
      const isTableCtx =
        contentRoot.tagName === "TBODY" ||
        contentRoot.tagName === "TABLE" ||
        contentRoot.tagName === "THEAD" ||
        contentRoot.tagName === "TFOOT";

      // Insert sections
      for (let i = 0; i < processedSections.length; i++) {
        const comment = doc.createComment(` section: ${sectionNames[i]} `);
        contentRoot.appendChild(comment);

        const sectionHtml = processedSections[i]!;
        if (isTableCtx) {
          const tempTable = doc.createElement("table");
          const tempTbody = doc.createElement("tbody");
          tempTable.appendChild(tempTbody);
          tempTbody.innerHTML = sectionHtml;
          while (tempTbody.firstChild) {
            contentRoot.appendChild(tempTbody.firstChild);
          }
        } else {
          const temp = doc.createElement("div");
          temp.innerHTML = sectionHtml;
          while (temp.firstChild) {
            contentRoot.appendChild(temp.firstChild);
          }
        }
      }

      // Inject styles into <head>
      if (headStyles) {
        const styleContainer = doc.createElement("div");
        styleContainer.innerHTML = headStyles;
        while (styleContainer.firstChild) {
          doc.head.appendChild(styleContainer.firstChild);
        }
      }

      // Reconstruct with doctype
      let doctypeStr = "";
      if (doc.doctype) {
        const dt = doc.doctype;
        doctypeStr = `<!DOCTYPE ${dt.name}${dt.publicId ? ` PUBLIC "${dt.publicId}"` : ""}${dt.systemId ? ` "${dt.systemId}"` : ""}>`;
      } else {
        const match = templateShell.match(/<!DOCTYPE[^>]*>/i);
        if (match) doctypeStr = match[0];
      }

      return (doctypeStr ? doctypeStr + "\n" : "") + doc.documentElement.outerHTML;
    }
  }

  // Default shell — fresh builder with no imported template
  const sectionHtml = processedSections
    .map((html, i) => `<!-- section: ${sectionNames[i]} -->\n${html}`)
    .join("\n");

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<style>
  body { margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; }
  table { border-collapse: collapse; }
  img { border: 0; display: block; }
</style>
${headStyles}
</head>
<body>
<center>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;">
${sectionHtml}
</table>
</center>
</body>
</html>`;
}

/**
 * Assembles sections into a complete email HTML document.
 * Structure-preserving: each section keeps its original HTML structure.
 * Applies slot fills, token overrides, HTML attributes, dark mode, MSO.
 */
export function useBuilderPreview(
  sections: BuilderSection[],
  templateShell?: string
): string | null {
  const assembled = useMemo(() => {
    if (sections.length === 0) return null;

    // Process each section (structure-preserving)
    const processedSections = sections.map((s) => {
      let html = processSection(s);

      // MSO ghost table wrapping (not content hiding)
      if (s.advanced.msoConditional) {
        html = wrapMsoGhostTable(html);
      }

      return html;
    });

    const sectionNames = sections.map((s) =>
      DOMPurify.sanitize(s.componentName)
    );

    // Collect section-scoped CSS in <head> (not between <tr> elements)
    const scopedCssRules: string[] = [];
    for (const s of sections) {
      if (s.css) {
        const safeId = sanitizeSelectorValue(s.id);
        // Strip dangerous at-rules before scoping
        const safeCss = s.css
          .replace(/@import\b[^;]*;/gi, "/* @import stripped */")
          .replace(/@font-face\s*\{[^}]*src\s*:[^}]*url\s*\([^}]*\}[^}]*\}/gi, "/* @font-face with url stripped */");
        // Scope section CSS with data-section-id selector
        scopedCssRules.push(
          safeCss
            .split("\n")
            .map((line) => {
              const trimmed = line.trim();
              if (!trimmed || trimmed.startsWith("@") || trimmed === "}" || trimmed === "{") {
                return line;
              }
              // Prefix selectors with section scope (handles "} selector {" on same line)
              if (trimmed.includes("{")) {
                return line.replace(
                  /(?:^|(?<=\}))\s*([^{}]+)\{/g,
                  ` [data-section-id="${safeId}"] $1{`
                );
              }
              return line;
            })
            .join("\n")
        );
      }
    }

    const sectionCss = scopedCssRules.length > 0
      ? `<style>${scopedCssRules.join("\n")}</style>`
      : "";
    const responsiveCss = buildResponsiveCss(sections);
    const darkModeCss = buildDarkModeCss(sections);
    const headStyles = [sectionCss, responsiveCss, darkModeCss]
      .filter(Boolean)
      .join("\n");

    return assembleDocument(
      processedSections,
      sectionNames,
      headStyles,
      templateShell
    );
  }, [sections, templateShell]);

  return assembled;
}

/** Creates default values for new BuilderSection fields */
export function createSectionDefaults(): Pick<BuilderSection, "slotDefinitions" | "defaultTokens" | "responsive" | "advanced"> {
  return {
    slotDefinitions: [],
    defaultTokens: null,
    responsive: { ...DEFAULT_RESPONSIVE },
    advanced: { ...DEFAULT_ADVANCED },
  };
}
