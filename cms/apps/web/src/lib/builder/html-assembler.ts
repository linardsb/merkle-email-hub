"use client";

import DOMPurify from "dompurify";
import type { BuilderSection } from "@/types/visual-builder";
import { findContentRoot } from "@/lib/builder-sync/ast-mapper";

// ── Sanitization ──

function sanitizeCssValue(value: string): string {
  return value
    .replace(/expression\s*\(/gi, "")
    .replace(/behavior\s*:/gi, "")
    .replace(/url\s*\([^)]*(?:javascript|vbscript|data\s*:\s*text\/html)[^)]*\)/gi, "")
    .replace(/<|>/g, "");
}

function sanitizeCssProperty(prop: string): string {
  return prop.replace(/[^a-zA-Z0-9-]/g, "");
}

function isSafeUri(uri: string): boolean {
  const trimmed = uri.trim().toLowerCase();
  if (/^(javascript|vbscript|data\s*:\s*text\/html):/i.test(trimmed)) return false;
  return true;
}

function sanitizeSelectorValue(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "");
}

// ── Token override system ──

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
export function processSection(section: BuilderSection): string {
  const temp = document.createElement("div");
  temp.innerHTML = section.html;
  const root = temp.firstElementChild;
  if (!root) return section.html;

  root.setAttribute("data-section-id", section.id);
  if (section.componentId) {
    root.setAttribute("data-component-id", String(section.componentId));
    root.setAttribute("data-component-name", section.componentName);
  }

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
          } catch {
            /* leave as-is */
          }
        } else {
          slotEl.innerHTML = DOMPurify.sanitize(fill);
        }
      }
    }
  }

  const tokenStyles = buildTokenStyles(section.tokenOverrides);
  if (tokenStyles) {
    const existing = root.getAttribute("style") ?? "";
    root.setAttribute("style", existing ? `${existing};${tokenStyles}` : tokenStyles);
  }

  for (const [key, val] of Object.entries(section.advanced.htmlAttributes)) {
    if (/^on/i.test(key) || key === "style") continue;
    if (/^(javascript|data|vbscript):/i.test(val)) continue;
    root.setAttribute(key, val);
  }

  if (section.advanced.customCssClass) {
    const safeClass = section.advanced.customCssClass.replace(/[^a-zA-Z0-9_\-\s]/g, "");
    if (safeClass) {
      root.classList.add(...safeClass.split(/\s+/).filter(Boolean));
    }
  }

  return root.outerHTML;
}

// ── Responsive CSS generation ──

export function buildResponsiveCss(sections: BuilderSection[]): string {
  const rules: string[] = [];
  for (const s of sections) {
    const r = s.responsive;
    const safeId = sanitizeSelectorValue(s.id);
    const sel = `[data-section-id="${safeId}"]`;

    if (r.stackOnMobile) {
      rules.push(
        `@media (max-width:480px) { ${sel} td { display:block !important; width:100% !important; } }`,
      );
      rules.push(`@media (max-width:480px) { ${sel} table { width:100% !important; } }`);
    }
    if (r.fullWidthImageOnMobile) {
      rules.push(
        `@media (max-width:480px) { ${sel} img { width:100% !important; height:auto !important; } }`,
      );
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
 * Build dark mode CSS from section overrides. Generates both
 * `@media (prefers-color-scheme:dark)` and `[data-ogsc]` rules for
 * broad client support (Apple Mail, Outlook app, etc.).
 */
export function buildDarkModeCss(sections: BuilderSection[]): string {
  const rules: string[] = [];
  for (const s of sections) {
    const entries = Object.entries(s.advanced.darkModeOverrides);
    if (entries.length === 0) continue;
    const safeId = sanitizeSelectorValue(s.id);
    const decls = entries
      .map(([prop, val]) => `${sanitizeCssProperty(prop)}:${sanitizeCssValue(val)}`)
      .join(";");
    rules.push(`@media (prefers-color-scheme:dark) { [data-section-id="${safeId}"] { ${decls} } }`);
    rules.push(`[data-ogsc] [data-section-id="${safeId}"] { ${decls} }`);
  }
  return rules.length > 0 ? `<style>${rules.join("\n")}</style>` : "";
}

// ── Section-scoped CSS ──

/**
 * Scope each section's `css` field with `[data-section-id="..."]` and strip
 * dangerous at-rules. Used as the third <style> block in the head.
 */
export function buildScopedSectionCss(sections: BuilderSection[]): string {
  const scopedCssRules: string[] = [];
  for (const s of sections) {
    if (!s.css) continue;
    const safeId = sanitizeSelectorValue(s.id);
    const safeCss = s.css
      .replace(/@import\b[^;]*;/gi, "/* @import stripped */")
      .replace(
        /@font-face\s*\{[^}]*src\s*:[^}]*url\s*\([^}]*\}[^}]*\}/gi,
        "/* @font-face with url stripped */",
      );
    scopedCssRules.push(
      safeCss
        .split("\n")
        .map((line) => {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith("@") || trimmed === "}" || trimmed === "{") {
            return line;
          }
          if (trimmed.includes("{")) {
            return line.replace(
              /(?:^|(?<=\}))\s*([^{}]+)\{/g,
              ` [data-section-id="${safeId}"] $1{`,
            );
          }
          return line;
        })
        .join("\n"),
    );
  }
  return scopedCssRules.length > 0 ? `<style>${scopedCssRules.join("\n")}</style>` : "";
}

// ── MSO conditional wrapping ──

/**
 * Wrap content with ghost table pattern for Outlook. Does NOT hide content
 * from non-Outlook — provides table structure for Outlook while modern
 * clients see the div/content directly.
 */
export function wrapMsoGhostTable(html: string): string {
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
export function assembleDocument(
  processedSections: string[],
  sectionNames: string[],
  headStyles: string,
  templateShell?: string,
): string {
  if (templateShell) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(templateShell, "text/html");
    const contentRoot = findContentRoot(doc.body, false);
    if (contentRoot) {
      const existingContent = Array.from(contentRoot.children).filter(
        (el) => !["STYLE", "SCRIPT", "META", "LINK"].includes(el.tagName),
      );
      for (const child of existingContent) child.remove();

      const textNodes: ChildNode[] = [];
      for (const node of Array.from(contentRoot.childNodes)) {
        if (node.nodeType === Node.TEXT_NODE || node.nodeType === Node.COMMENT_NODE) {
          textNodes.push(node as ChildNode);
        }
      }
      for (const node of textNodes) node.remove();

      const isTableCtx =
        contentRoot.tagName === "TBODY" ||
        contentRoot.tagName === "TABLE" ||
        contentRoot.tagName === "THEAD" ||
        contentRoot.tagName === "TFOOT";

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

      if (headStyles) {
        const styleContainer = doc.createElement("div");
        styleContainer.innerHTML = headStyles;
        while (styleContainer.firstChild) {
          doc.head.appendChild(styleContainer.firstChild);
        }
      }

      const bodyStyle = doc.body.getAttribute("style") ?? "";
      if (!/background(-color)?\s*:/i.test(bodyStyle)) {
        doc.body.setAttribute(
          "style",
          bodyStyle ? `${bodyStyle}; background-color:#ffffff;` : "background-color:#ffffff;",
        );
      }

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
<div style="max-width:600px;margin:0 auto;">
${sectionHtml}
</div>
</center>
</body>
</html>`;
}

// ── Top-level assembly ──

/**
 * Assemble a list of builder sections into a complete email HTML document.
 * Returns `null` for empty section lists.
 *
 * Pipeline: per-section processing (slots, tokens, attrs, MSO wrap) → head
 * styles (scoped section CSS, responsive, dark mode) → document assembly.
 */
export function assembleEmailHtml(
  sections: BuilderSection[],
  templateShell?: string,
): string | null {
  if (sections.length === 0) return null;

  const processedSections = sections.map((s) => {
    let html = processSection(s);
    if (s.advanced.msoConditional) {
      html = wrapMsoGhostTable(html);
    }
    return html;
  });

  const sectionNames = sections.map((s) => DOMPurify.sanitize(s.componentName));

  const sectionCss = buildScopedSectionCss(sections);
  const responsiveCss = buildResponsiveCss(sections);
  const darkModeCss = buildDarkModeCss(sections);
  const headStyles = [sectionCss, responsiveCss, darkModeCss].filter(Boolean).join("\n");

  return assembleDocument(processedSections, sectionNames, headStyles, templateShell);
}
