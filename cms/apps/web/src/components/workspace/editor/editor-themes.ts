import { EditorView } from "@codemirror/view";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { tags as t } from "@lezer/highlight";
import type { Extension } from "@codemirror/state";

// --- Light theme ---

const lightEditorTheme = EditorView.theme(
  {
    "&": {
      backgroundColor: "#ffffff",
      color: "#1e293b",
    },
    ".cm-cursor": { borderLeftColor: "#1e293b" },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
      backgroundColor: "#bfdbfe",
    },
    ".cm-activeLine": { backgroundColor: "#f1f5f9" },
    ".cm-gutters": {
      backgroundColor: "#ffffff",
      color: "#94a3b8",
      borderRight: "none",
    },
    ".cm-activeLineGutter": { color: "#475569" },
    ".cm-matchingBracket": {
      backgroundColor: "#dbeafe",
      outline: "1px solid #3b82f6",
    },
  },
  { dark: false }
);

const lightHighlightStyle = HighlightStyle.define([
  // HTML
  { tag: t.tagName, color: "#2563eb" },
  { tag: t.attributeName, color: "#0891b2" },
  { tag: t.attributeValue, color: "#16a34a" },
  { tag: t.angleBracket, color: "#64748b" },
  { tag: t.content, color: "#1e293b" },
  // Comments
  { tag: t.comment, color: "#94a3b8" },
  { tag: t.blockComment, color: "#94a3b8" },
  // Strings
  { tag: t.string, color: "#16a34a" },
  // Numbers
  { tag: t.number, color: "#d97706" },
  // Keywords
  { tag: t.keyword, color: "#2563eb" },
  { tag: t.operator, color: "#64748b" },
  // Liquid/Maizzle template tokens
  { tag: t.processingInstruction, color: "#7c3aed" },
  { tag: t.special(t.variableName), color: "#6d28d9" },
  { tag: t.special(t.keyword), color: "#2563eb" },
  { tag: t.special(t.string), color: "#16a34a" },
  { tag: t.special(t.number), color: "#d97706" },
  { tag: t.special(t.tagName), color: "#dc2626", fontWeight: "bold" },
  // YAML front matter
  { tag: t.meta, color: "#94a3b8", fontStyle: "italic" },
  // Entities
  { tag: t.character, color: "#d97706" },
]);

const lightTheme: Extension = [
  lightEditorTheme,
  syntaxHighlighting(lightHighlightStyle),
];

// --- Dark theme ---

const darkEditorTheme = EditorView.theme(
  {
    "&": {
      backgroundColor: "#0f172a",
      color: "#e2e8f0",
    },
    ".cm-cursor": { borderLeftColor: "#e2e8f0" },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
      backgroundColor: "#1e3a5f",
    },
    ".cm-activeLine": { backgroundColor: "#1e293b" },
    ".cm-gutters": {
      backgroundColor: "#0f172a",
      color: "#475569",
      borderRight: "none",
    },
    ".cm-activeLineGutter": { color: "#94a3b8" },
    ".cm-matchingBracket": {
      backgroundColor: "#1e3a5f",
      outline: "1px solid #3b82f6",
    },
  },
  { dark: true }
);

const darkHighlightStyle = HighlightStyle.define([
  // HTML
  { tag: t.tagName, color: "#60a5fa" },
  { tag: t.attributeName, color: "#22d3ee" },
  { tag: t.attributeValue, color: "#4ade80" },
  { tag: t.angleBracket, color: "#94a3b8" },
  { tag: t.content, color: "#e2e8f0" },
  // Comments
  { tag: t.comment, color: "#64748b" },
  { tag: t.blockComment, color: "#64748b" },
  // Strings
  { tag: t.string, color: "#4ade80" },
  // Numbers
  { tag: t.number, color: "#fbbf24" },
  // Keywords
  { tag: t.keyword, color: "#60a5fa" },
  { tag: t.operator, color: "#94a3b8" },
  // Liquid/Maizzle
  { tag: t.processingInstruction, color: "#a78bfa" },
  { tag: t.special(t.variableName), color: "#c4b5fd" },
  { tag: t.special(t.keyword), color: "#60a5fa" },
  { tag: t.special(t.string), color: "#4ade80" },
  { tag: t.special(t.number), color: "#fbbf24" },
  { tag: t.special(t.tagName), color: "#f87171", fontWeight: "bold" },
  // YAML front matter
  { tag: t.meta, color: "#64748b", fontStyle: "italic" },
  // Entities
  { tag: t.character, color: "#fbbf24" },
]);

const darkTheme: Extension = [
  darkEditorTheme,
  syntaxHighlighting(darkHighlightStyle),
];

// --- Export ---

export function getEditorTheme(resolvedTheme: string | undefined): Extension {
  return resolvedTheme === "dark" ? darkTheme : lightTheme;
}
