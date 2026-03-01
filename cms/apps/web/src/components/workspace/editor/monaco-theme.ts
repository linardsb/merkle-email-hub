import type * as Monaco from "monaco-editor";

let defined = false;

export function defineEditorThemes(monaco: typeof Monaco): void {
  if (defined) return;
  defined = true;

  monaco.editor.defineTheme("email-hub-light", {
    base: "vs",
    inherit: true,
    rules: [
      { token: "delimiter.liquid", foreground: "7c3aed" },
      { token: "variable.liquid", foreground: "6d28d9" },
      { token: "keyword.liquid", foreground: "2563eb" },
      { token: "string.liquid", foreground: "16a34a" },
      { token: "number.liquid", foreground: "d97706" },
      { token: "operator.liquid", foreground: "64748b" },
      { token: "tag.maizzle", foreground: "dc2626", fontStyle: "bold" },
      { token: "comment.yaml", foreground: "94a3b8", fontStyle: "italic" },
      { token: "comment.mso", foreground: "64748b", fontStyle: "italic" },
      { token: "comment.html", foreground: "94a3b8" },
      { token: "attribute.name.html", foreground: "0891b2" },
      { token: "attribute.value.html", foreground: "16a34a" },
      { token: "delimiter.html", foreground: "64748b" },
      { token: "string.html.entity", foreground: "d97706" },
    ],
    colors: {
      "editor.background": "#ffffff",
      "editor.foreground": "#1e293b",
      "editor.lineHighlightBackground": "#f1f5f9",
      "editor.selectionBackground": "#bfdbfe",
      "editorLineNumber.foreground": "#94a3b8",
      "editorLineNumber.activeForeground": "#475569",
      "editorBracketMatch.background": "#dbeafe",
      "editorBracketMatch.border": "#3b82f6",
      "editor.inactiveSelectionBackground": "#e2e8f0",
    },
  });

  monaco.editor.defineTheme("email-hub-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "delimiter.liquid", foreground: "a78bfa" },
      { token: "variable.liquid", foreground: "c4b5fd" },
      { token: "keyword.liquid", foreground: "60a5fa" },
      { token: "string.liquid", foreground: "4ade80" },
      { token: "number.liquid", foreground: "fbbf24" },
      { token: "operator.liquid", foreground: "94a3b8" },
      { token: "tag.maizzle", foreground: "f87171", fontStyle: "bold" },
      { token: "comment.yaml", foreground: "64748b", fontStyle: "italic" },
      { token: "comment.mso", foreground: "94a3b8", fontStyle: "italic" },
      { token: "comment.html", foreground: "64748b" },
      { token: "attribute.name.html", foreground: "22d3ee" },
      { token: "attribute.value.html", foreground: "4ade80" },
      { token: "delimiter.html", foreground: "94a3b8" },
      { token: "string.html.entity", foreground: "fbbf24" },
    ],
    colors: {
      "editor.background": "#0f172a",
      "editor.foreground": "#e2e8f0",
      "editor.lineHighlightBackground": "#1e293b",
      "editor.selectionBackground": "#1e3a5f",
      "editorLineNumber.foreground": "#475569",
      "editorLineNumber.activeForeground": "#94a3b8",
      "editorBracketMatch.background": "#1e3a5f",
      "editorBracketMatch.border": "#3b82f6",
      "editor.inactiveSelectionBackground": "#1e293b",
    },
  });
}

export function getEditorTheme(
  resolvedTheme: string | undefined
): string {
  return resolvedTheme === "dark" ? "email-hub-dark" : "email-hub-light";
}
