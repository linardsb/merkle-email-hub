import type { editor } from "monaco-editor";

export interface EditorThemeOption {
  id: string;
  label: string;
  base: "light" | "dark";
}

export const DEFAULT_LIGHT_THEME = "vs";
export const DEFAULT_DARK_THEME = "vs-dark";

/** All available editor themes. */
export const EDITOR_THEMES: EditorThemeOption[] = [
  { id: "vs", label: "VS Light", base: "light" },
  { id: "vs-dark", label: "VS Dark", base: "dark" },
  { id: "hc-black", label: "High Contrast Dark", base: "dark" },
  { id: "hc-light", label: "High Contrast Light", base: "light" },
  { id: "monokai", label: "Monokai", base: "dark" },
  { id: "github-dark", label: "GitHub Dark", base: "dark" },
  { id: "solarized-dark", label: "Solarized Dark", base: "dark" },
  { id: "solarized-light", label: "Solarized Light", base: "light" },
  { id: "nord", label: "Nord", base: "dark" },
  { id: "dracula", label: "Dracula", base: "dark" },
];

export const monokaiTheme: editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "tag", foreground: "f92672" },
    { token: "attribute.name", foreground: "a6e22e" },
    { token: "attribute.value", foreground: "e6db74" },
    { token: "delimiter.html", foreground: "f8f8f2" },
    { token: "comment", foreground: "75715e" },
    { token: "string", foreground: "e6db74" },
    { token: "keyword", foreground: "f92672" },
    { token: "number", foreground: "ae81ff" },
    { token: "variable", foreground: "66d9ef" },
    { token: "operator", foreground: "f92672" },
  ],
  colors: {
    "editor.background": "#272822",
    "editor.foreground": "#f8f8f2",
    "editor.selectionBackground": "#49483e",
    "editor.lineHighlightBackground": "#3e3d32",
    "editorLineNumber.foreground": "#90908a",
    "editorLineNumber.activeForeground": "#c2c2bf",
    "editorGutter.background": "#272822",
  },
};

export const githubDarkTheme: editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "tag", foreground: "7ee787" },
    { token: "attribute.name", foreground: "79c0ff" },
    { token: "attribute.value", foreground: "a5d6ff" },
    { token: "delimiter.html", foreground: "c9d1d9" },
    { token: "comment", foreground: "8b949e" },
    { token: "string", foreground: "a5d6ff" },
    { token: "keyword", foreground: "ff7b72" },
    { token: "number", foreground: "79c0ff" },
    { token: "variable", foreground: "ffa657" },
    { token: "operator", foreground: "ff7b72" },
  ],
  colors: {
    "editor.background": "#0d1117",
    "editor.foreground": "#c9d1d9",
    "editor.selectionBackground": "#264f78",
    "editor.lineHighlightBackground": "#161b22",
    "editorLineNumber.foreground": "#6e7681",
    "editorLineNumber.activeForeground": "#c9d1d9",
    "editorGutter.background": "#0d1117",
  },
};

export const solarizedDarkTheme: editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "tag", foreground: "268bd2" },
    { token: "attribute.name", foreground: "b58900" },
    { token: "attribute.value", foreground: "2aa198" },
    { token: "delimiter.html", foreground: "839496" },
    { token: "comment", foreground: "586e75" },
    { token: "string", foreground: "2aa198" },
    { token: "keyword", foreground: "859900" },
    { token: "number", foreground: "d33682" },
    { token: "variable", foreground: "b58900" },
    { token: "operator", foreground: "859900" },
  ],
  colors: {
    "editor.background": "#002b36",
    "editor.foreground": "#839496",
    "editor.selectionBackground": "#073642",
    "editor.lineHighlightBackground": "#073642",
    "editorLineNumber.foreground": "#586e75",
    "editorLineNumber.activeForeground": "#93a1a1",
    "editorGutter.background": "#002b36",
  },
};

export const solarizedLightTheme: editor.IStandaloneThemeData = {
  base: "vs",
  inherit: true,
  rules: [
    { token: "tag", foreground: "268bd2" },
    { token: "attribute.name", foreground: "b58900" },
    { token: "attribute.value", foreground: "2aa198" },
    { token: "delimiter.html", foreground: "657b83" },
    { token: "comment", foreground: "93a1a1" },
    { token: "string", foreground: "2aa198" },
    { token: "keyword", foreground: "859900" },
    { token: "number", foreground: "d33682" },
    { token: "variable", foreground: "b58900" },
    { token: "operator", foreground: "859900" },
  ],
  colors: {
    "editor.background": "#fdf6e3",
    "editor.foreground": "#657b83",
    "editor.selectionBackground": "#eee8d5",
    "editor.lineHighlightBackground": "#eee8d5",
    "editorLineNumber.foreground": "#93a1a1",
    "editorLineNumber.activeForeground": "#586e75",
    "editorGutter.background": "#fdf6e3",
  },
};

export const nordTheme: editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "tag", foreground: "81a1c1" },
    { token: "attribute.name", foreground: "8fbcbb" },
    { token: "attribute.value", foreground: "a3be8c" },
    { token: "delimiter.html", foreground: "d8dee9" },
    { token: "comment", foreground: "616e88" },
    { token: "string", foreground: "a3be8c" },
    { token: "keyword", foreground: "81a1c1" },
    { token: "number", foreground: "b48ead" },
    { token: "variable", foreground: "d8dee9" },
    { token: "operator", foreground: "81a1c1" },
  ],
  colors: {
    "editor.background": "#2e3440",
    "editor.foreground": "#d8dee9",
    "editor.selectionBackground": "#434c5e",
    "editor.lineHighlightBackground": "#3b4252",
    "editorLineNumber.foreground": "#4c566a",
    "editorLineNumber.activeForeground": "#d8dee9",
    "editorGutter.background": "#2e3440",
  },
};

export const draculaTheme: editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "tag", foreground: "ff79c6" },
    { token: "attribute.name", foreground: "50fa7b" },
    { token: "attribute.value", foreground: "f1fa8c" },
    { token: "delimiter.html", foreground: "f8f8f2" },
    { token: "comment", foreground: "6272a4" },
    { token: "string", foreground: "f1fa8c" },
    { token: "keyword", foreground: "ff79c6" },
    { token: "number", foreground: "bd93f9" },
    { token: "variable", foreground: "8be9fd" },
    { token: "operator", foreground: "ff79c6" },
  ],
  colors: {
    "editor.background": "#282a36",
    "editor.foreground": "#f8f8f2",
    "editor.selectionBackground": "#44475a",
    "editor.lineHighlightBackground": "#44475a",
    "editorLineNumber.foreground": "#6272a4",
    "editorLineNumber.activeForeground": "#f8f8f2",
    "editorGutter.background": "#282a36",
  },
};

/** Register all custom themes with Monaco. Call once during editor setup. */
export function registerAllThemes(monaco: {
  editor: { defineTheme(name: string, data: editor.IStandaloneThemeData): void };
}) {
  monaco.editor.defineTheme("monokai", monokaiTheme);
  monaco.editor.defineTheme("github-dark", githubDarkTheme);
  monaco.editor.defineTheme("solarized-dark", solarizedDarkTheme);
  monaco.editor.defineTheme("solarized-light", solarizedLightTheme);
  monaco.editor.defineTheme("nord", nordTheme);
  monaco.editor.defineTheme("dracula", draculaTheme);
}
