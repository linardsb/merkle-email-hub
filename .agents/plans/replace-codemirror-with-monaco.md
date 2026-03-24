# Plan: Replace CodeMirror with Monaco Editor

## Context

Replace CodeMirror v6 (`@uiw/react-codemirror`) with Monaco Editor (VS Code's engine) for minimap, multi-cursor, find/replace UI, command palette, and VS Code familiarity. MIT, ~2.5MB, battle-tested.

### API Mapping

| Feature | CodeMirror | Monaco |
|---------|-----------|--------|
| Wrapper | `@uiw/react-codemirror` | `@monaco-editor/react` |
| Language | `StreamParser` | Monarch tokenizer |
| Linters | `linter()` → `Diagnostic[]` | `setModelMarkers()` → `IMarkerData[]` |
| Themes | `EditorView.theme()` + `HighlightStyle` | `defineTheme()` |
| Snippets | `snippetCompletion()` | `registerCompletionItemProvider()` |
| Bridge | CM6 `dispatch()` | `executeEdits()` + `deltaDecorations()` |
| Collab | `y-codemirror.next` | `y-monaco` |
| Word wrap | `Compartment.reconfigure()` | `updateOptions({ wordWrap })` |
| Keys | `keymap.of()` | `addCommand()` |
| Cursor | `updateListener` | `onDidChangeCursorPosition()` |
| Highlights | `StateField` + `Decoration` | `deltaDecorations()` |
| DnD | CM6 `domEventHandlers` | DOM `drop` event |

## Files to Rewrite (same paths)

- `cms/apps/web/src/components/workspace/editor/code-editor.tsx` — Monaco wrapper
- `cms/apps/web/src/components/workspace/editor/maizzle-language.ts` — Monarch tokenizer
- `cms/apps/web/src/components/workspace/editor/editor-themes.ts` — Monaco theme defs
- `cms/apps/web/src/components/workspace/editor/css-diagnostics.ts` — Markers API
- `cms/apps/web/src/components/workspace/editor/brand-linter.ts` — Markers API
- `cms/apps/web/src/hooks/use-editor-bridge.ts` — Monaco editor API
- `cms/apps/web/src/lib/collaboration/editor-binding.ts` — y-monaco binding

## Files to Modify

- `cms/apps/web/package.json` — swap deps
- `cms/apps/web/src/app/globals.css` — add decoration CSS classes
- `cms/apps/web/next.config.ts` — Monaco loader config (optional)

## Unchanged (no editor dependency)

`editor-toolbar.tsx`, `editor-panel.tsx`, `caniemail-data.ts`, all builder-sync files, workspace page

## Steps

### 1. Swap packages

```bash
cd cms/apps/web
pnpm add @monaco-editor/react monaco-editor y-monaco
pnpm remove @uiw/react-codemirror @codemirror/autocomplete @codemirror/lang-css \
  @codemirror/lang-html @codemirror/language @codemirror/lint @codemirror/state \
  @codemirror/theme-one-dark @codemirror/view @lezer/highlight y-codemirror.next
```

### 2. Rewrite `maizzle-language.ts` — Monarch tokenizer

Export `LANGUAGE_ID = "maizzle-html"`, `monarchTokensProvider`, `languageConfiguration`, and `snippetCompletions`.

```ts
import type { languages } from "monaco-editor";

export const LANGUAGE_ID = "maizzle-html";

export const monarchTokensProvider: languages.IMonarchLanguage = {
  defaultToken: "",
  ignoreCase: true,
  maizzleTags: [
    "extends", "block", "component", "slot", "fill", "stack",
    "push", "each", "if", "elseif", "else", "switch", "case",
    "default", "raw", "markdown", "outlook", "not-outlook",
  ],
  tokenizer: {
    root: [
      [/^---\s*$/, { token: "meta", next: "@yamlFrontMatter" }],
      [/\{\{\{/, { token: "delimiter.expression", next: "@maizzleExpr" }],
      [/\{\{-?/, { token: "delimiter.expression", next: "@liquidOutput" }],
      [/\{%-?/, { token: "delimiter.expression", next: "@liquidTag" }],
      [/<!--\[if\s+(?:mso|gte\s+mso|lte\s+mso|gt\s+mso|lt\s+mso)[^\]]*\]>/, "comment"],
      [/<!\[endif\]-->/, "comment"],
      [/<!--/, { token: "comment", next: "@htmlComment" }],
      [/<\/?(@maizzleTags)(?=[\s/>])/, "tag.maizzle"],
      [/<\/?/, { token: "delimiter.html", next: "@htmlTag" }],
      [/&\w+;/, "string.escape"],
      [/[^<{&]+/, ""],
    ],
    yamlFrontMatter: [
      [/^---\s*$/, { token: "meta", next: "@pop" }],
      [/.*/, "meta.content"],
    ],
    maizzleExpr: [
      [/\}\}\}/, { token: "delimiter.expression", next: "@pop" }],
      [/"[^"]*"|'[^']*'/, "string"],
      [/\|/, "delimiter"],
      [/[a-zA-Z_]\w*/, "variable"],
      [/./, "variable"],
    ],
    liquidOutput: [
      [/-?\}\}/, { token: "delimiter.expression", next: "@pop" }],
      [/"[^"]*"|'[^']*'/, "string"],
      [/\|/, "delimiter"],
      [/\d+(\.\d+)?/, "number"],
      [/(?:true|false|nil|null|blank|empty)\b/, "keyword"],
      [/[a-zA-Z_][\w.]*/, "variable"],
      [/./, "variable"],
    ],
    liquidTag: [
      [/-?%\}/, { token: "delimiter.expression", next: "@pop" }],
      [/"[^"]*"|'[^']*'/, "string"],
      [/[=!<>]=?|!=/, "operator"],
      [/\d+(\.\d+)?/, "number"],
      // All liquid keywords inline in the regex:
      [/(?:if|elsif|else|endif|unless|endunless|for|endfor|case|when|endcase|assign|capture|endcapture|comment|endcomment|include|render|raw|endraw|tablerow|endtablerow|break|continue|cycle|increment|decrement)\b/, "keyword"],
      [/(?:true|false|nil|null|blank|empty)\b/, "keyword"],
      [/(?:and|or|not|contains|in)\b/, "keyword"],
      [/[a-zA-Z_]\w*/, "variable"],
      [/./, "variable"],
    ],
    htmlTag: [
      [/\/?>/, { token: "delimiter.html", next: "@pop" }],
      [/\{\{-?/, { token: "delimiter.expression", next: "@liquidOutput" }],
      [/\{%-?/, { token: "delimiter.expression", next: "@liquidTag" }],
      [/[a-zA-Z][\w-]*(?=\s*=)/, "attribute.name"],
      [/=/, "delimiter"],
      [/"[^"]*"|'[^']*'/, "attribute.value"],
      [/[a-zA-Z][\w-]*/, "tag"],
      [/\s+/, ""],
    ],
    htmlComment: [
      [/--!?>/, { token: "comment", next: "@pop" }],
      [/./, "comment"],
    ],
  },
};

export const languageConfiguration: languages.LanguageConfiguration = {
  comments: { blockComment: ["<!--", "-->"] },
  brackets: [["<", ">"], ["{", "}"], ["(", ")"], ["[", "]"]],
  autoClosingPairs: [
    { open: "{", close: "}" }, { open: "[", close: "]" },
    { open: "(", close: ")" }, { open: '"', close: '"' },
    { open: "'", close: "'" }, { open: "<!--", close: "-->" },
  ],
  surroundingPairs: [
    { open: '"', close: '"' }, { open: "'", close: "'" }, { open: "<", close: ">" },
  ],
};

// Same 7 snippets, Monaco syntax (${1:placeholder}, $0)
export const snippetCompletions = [
  { label: "<extends>", detail: "Maizzle layout extends",
    insertText: '<extends src="${1:src/layouts/main.html}">\n\t$0\n</extends>' },
  { label: "<block>", detail: "Maizzle content block",
    insertText: '<block name="${1:content}">\n\t$0\n</block>' },
  { label: "<component>", detail: "Maizzle component include",
    insertText: '<component src="${1:src/components/}">\n\t$0\n</component>' },
  { label: "{{ }}", detail: "Liquid output tag", insertText: "{{ ${1:variable} }}" },
  { label: "{% if %}", detail: "Liquid if block",
    insertText: '{% if ${1:condition} %}\n\t$0\n{% endif %}' },
  { label: "{% for %}", detail: "Liquid for loop",
    insertText: '{% for ${1:item} in ${2:collection} %}\n\t$0\n{% endfor %}' },
  { label: "<!--[if mso]>", detail: "MSO conditional for Outlook",
    insertText: "<!--[if mso]>\n$0\n<![endif]-->" },
];
```

### 3. Rewrite `editor-themes.ts`

```ts
import type { editor } from "monaco-editor";

export const LIGHT_THEME_ID = "merkle-light";
export const DARK_THEME_ID = "merkle-dark";

export const lightTheme: editor.IStandaloneThemeData = {
  base: "vs", inherit: true,
  rules: [
    { token: "tag", foreground: "2563eb" },
    { token: "tag.maizzle", foreground: "dc2626", fontStyle: "bold" },
    { token: "attribute.name", foreground: "0891b2" },
    { token: "attribute.value", foreground: "16a34a" },
    { token: "delimiter.html", foreground: "64748b" },
    { token: "delimiter.expression", foreground: "7c3aed" },
    { token: "variable", foreground: "6d28d9" },
    { token: "keyword", foreground: "2563eb" },
    { token: "string", foreground: "16a34a" },
    { token: "number", foreground: "d97706" },
    { token: "operator", foreground: "64748b" },
    { token: "comment", foreground: "94a3b8" },
    { token: "meta", foreground: "94a3b8", fontStyle: "italic" },
    { token: "meta.content", foreground: "94a3b8", fontStyle: "italic" },
    { token: "string.escape", foreground: "d97706" },
  ],
  colors: {
    "editor.background": "#ffffff", "editor.foreground": "#1e293b",
    "editor.selectionBackground": "#bfdbfe", "editor.lineHighlightBackground": "#f1f5f9",
    "editorLineNumber.foreground": "#94a3b8", "editorLineNumber.activeForeground": "#475569",
    "editorBracketMatch.background": "#dbeafe", "editorBracketMatch.border": "#3b82f6",
    "editorGutter.background": "#ffffff",
  },
};

export const darkTheme: editor.IStandaloneThemeData = {
  base: "vs-dark", inherit: true,
  rules: [
    { token: "tag", foreground: "60a5fa" },
    { token: "tag.maizzle", foreground: "f87171", fontStyle: "bold" },
    { token: "attribute.name", foreground: "22d3ee" },
    { token: "attribute.value", foreground: "4ade80" },
    { token: "delimiter.html", foreground: "94a3b8" },
    { token: "delimiter.expression", foreground: "a78bfa" },
    { token: "variable", foreground: "c4b5fd" },
    { token: "keyword", foreground: "60a5fa" },
    { token: "string", foreground: "4ade80" },
    { token: "number", foreground: "fbbf24" },
    { token: "operator", foreground: "94a3b8" },
    { token: "comment", foreground: "64748b" },
    { token: "meta", foreground: "64748b", fontStyle: "italic" },
    { token: "meta.content", foreground: "64748b", fontStyle: "italic" },
    { token: "string.escape", foreground: "fbbf24" },
  ],
  colors: {
    "editor.background": "#0f172a", "editor.foreground": "#e2e8f0",
    "editor.selectionBackground": "#1e3a5f", "editor.lineHighlightBackground": "#1e293b",
    "editorLineNumber.foreground": "#475569", "editorLineNumber.activeForeground": "#94a3b8",
    "editorBracketMatch.background": "#1e3a5f", "editorBracketMatch.border": "#3b82f6",
    "editorGutter.background": "#0f172a",
  },
};
```

### 4. Rewrite `css-diagnostics.ts`

```ts
import type { editor } from "monaco-editor";
import { cssPropertyRules } from "./caniemail-data";

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function computeCssMarkers(model: editor.ITextModel): editor.IMarkerData[] {
  const content = model.getValue();
  const markers: editor.IMarkerData[] = [];

  for (const rule of cssPropertyRules) {
    const pattern = rule.value
      ? new RegExp(`${escapeRegex(rule.property)}\\s*:\\s*${escapeRegex(rule.value)}`, "gi")
      : new RegExp(`${escapeRegex(rule.property)}\\s*:`, "gi");

    let match: RegExpExecArray | null;
    while ((match = pattern.exec(content)) !== null) {
      const startPos = model.getPositionAt(match.index);
      const endPos = model.getPositionAt(match.index + match[0].length);
      markers.push({
        severity: rule.severity === "error" ? 8 : 4, // MarkerSeverity.Error : Warning
        message: `${rule.reason}\nUnsupported in: ${rule.unsupportedClients.join(", ")}`,
        source: "Can I Email",
        startLineNumber: startPos.lineNumber, startColumn: startPos.column,
        endLineNumber: endPos.lineNumber, endColumn: endPos.column,
      });
    }
  }
  return markers;
}
```

### 5. Rewrite `brand-linter.ts`

Same pattern as step 4 — `computeBrandMarkers(model: ITextModel, config: BrandConfig): IMarkerData[]`. Keep all 3 checks (off-brand hex, off-brand font, forbidden patterns) with identical regex logic. Only change: offset→position via `model.getPositionAt()`, severity `4` (Warning) for color/font, `8` (Error) for forbidden patterns.

### 6. Rewrite `use-editor-bridge.ts`

Change `CodeEditorHandle` interface:
```ts
export interface CodeEditorHandle {
  getEditor(): monacoEditor.IStandaloneCodeEditor | null;
}
```

Track decorations at module level: `let activeDecorations: string[] = [];`

All 9 methods rewritten with Monaco API:

```ts
// insertAtCursor — get position, executeEdits, focus
const position = editor.getPosition();
editor.executeEdits("editor-bridge", [{
  range: { startLineNumber: position.lineNumber, startColumn: position.column,
           endLineNumber: position.lineNumber, endColumn: position.column },
  text: cssText,
}]);

// findAndHighlight — model.findMatches + deltaDecorations + revealPositionInCenter
const matches = model.findMatches(searchText, false, false, false, null, false);
activeDecorations = editor.deltaDecorations(activeDecorations,
  matches.map((m) => ({ range: m.range, options: { className: "monaco-token-highlight" } }))
);
editor.revealPositionInCenter({ lineNumber: first.startLineNumber, column: first.startColumn });

// clearHighlights
activeDecorations = editor.deltaDecorations(activeDecorations, []);

// replaceInSelection — getSelection, getValueInRange, regex replace, executeEdits
const selection = editor.getSelection();
const selectedText = model.getValueInRange(selection);
const replaced = selectedText.replace(/#[a-f\d]{6}/gi, newHex);
editor.executeEdits("editor-bridge", [{ range: selection, text: replaced }]);

// insertAtOffset — model.getPositionAt(offset) + executeEdits
// replaceAll — findMatches reversed + executeEdits
// insertCssVariablesBlock — same <style>/<head> regex, model.getPositionAt for insert position
// spotlight — deltaDecorations with "monaco-token-spotlight" class
```

### 7. Rewrite `editor-binding.ts` — y-monaco

```ts
import * as Y from "yjs";
import { MonacoBinding } from "y-monaco";
import type { editor as monacoEditor } from "monaco-editor";
import type { Awareness } from "y-protocols/awareness";
import type { CollabUser } from "./awareness";
import { setLocalUser } from "./awareness";

export interface CollaborativeEditorConfig {
  doc: Y.Doc;
  awareness: Awareness;
  user: CollabUser;
  fieldName?: string;
}

export function createCollabBinding(
  config: CollaborativeEditorConfig,
  editor: monacoEditor.IStandaloneCodeEditor,
): { dispose: () => void } {
  const { doc, awareness, user, fieldName = "content" } = config;
  const ytext = doc.getText(fieldName);
  setLocalUser(awareness, user);
  const model = editor.getModel();
  if (!model) throw new Error("Editor model not available");
  const binding = new MonacoBinding(ytext, model, new Set([editor]), awareness);
  return { dispose: () => binding.destroy() };
}

// getDocumentContent and initDocumentContent unchanged — no editor dependency
```

### 8. Rewrite `code-editor.tsx`

Core component using `Editor` from `@monaco-editor/react`.

**Props interface:** identical to current (`CodeEditorProps` with value, onChange, onSave, saveStatus, readOnly, brandConfig, onBrandViolationsChange, onCursorOffsetChange, onSelectionChange, collaborative).

**Module-level flag:** `let languageRegistered = false` — register language/themes/completions once.

**onMount callback (`handleEditorDidMount: OnMount`):**
1. Store editor in `editorInstanceRef`
2. If `!languageRegistered`: `monaco.languages.register({ id: LANGUAGE_ID })`, set Monarch provider, set language config, register completion provider (map `snippetCompletions` to `CompletionItem` with `InsertAsSnippet` rule), `defineTheme` for both themes. Set flag.
3. `monaco.editor.setTheme(themeId)`
4. `editor.addCommand(CtrlCmd | KeyS, () => onSaveRef.current?.())`
5. `editor.onDidChangeCursorPosition` → setLine, setCol, call onCursorOffsetChange
6. `editor.onDidChangeCursorSelection` → call onSelectionChange
7. `editor.onDidChangeModelContent` → trigger debounced linters (300ms)
8. DOM `drop` listener on `editor.getDomNode()` for `application/x-design-token`
9. Initial lint pass
10. If `collaborative`, call `createCollabBinding()`, store dispose ref

**Linter runner (debounced 300ms):**
```ts
const cssMarkers = computeCssMarkers(model);
const brandMarkers = brandConfigRef.current ? computeBrandMarkers(model, brandConfigRef.current) : [];
monaco.editor.setModelMarkers(model, "css-diagnostics", cssMarkers);
monaco.editor.setModelMarkers(model, "brand-linter", brandMarkers);
setWarningCount(cssMarkers.length);
onBrandViolationsChangeRef.current?.(brandMarkers.length);
```

**Effects:**
- Clean up collab binding on unmount/config change
- Re-apply theme on `resolvedTheme` change: `monaco.editor.setTheme(themeId)`
- Re-run linters on `brandConfig` change

**Word wrap:** `editor.updateOptions({ wordWrap: next ? "on" : "off" })`

**Render:**
```tsx
<div className="flex h-full flex-col overflow-hidden">
  <EditorToolbar line={line} col={col} warningCount={warningCount}
    wordWrapEnabled={wordWrapEnabled} saveStatus={saveStatus ?? "idle"}
    onToggleWordWrap={handleToggleWordWrap} />
  <div className="relative min-h-0 flex-1">
    <Editor
      height="100%"
      language={LANGUAGE_ID}
      theme={themeId}
      value={collaborative ? undefined : value}
      onChange={collaborative ? undefined : handleChange}
      onMount={handleEditorDidMount}
      options={{
        readOnly, fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, monospace",
        tabSize: 2, minimap: { enabled: true },
        lineNumbers: "on", folding: true,
        bracketPairColorization: { enabled: true },
        matchBrackets: "always", autoClosingBrackets: "always",
        renderLineHighlight: "line", scrollBeyondLastLine: false,
        wordWrap: wordWrapEnabled ? "on" : "off",
        padding: { top: 8 }, automaticLayout: true,
        scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
      }}
    />
  </div>
</div>
```

### 9. Add decoration CSS

In `globals.css`:
```css
.monaco-token-highlight {
  background-color: rgba(255, 215, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.6);
}
.monaco-token-spotlight {
  background-color: rgba(147, 130, 255, 0.2);
  border-bottom: 2px solid rgba(147, 130, 255, 0.6);
}
```

### 10. Update tests

`editor-panel-sync.test.tsx` mocks `next/dynamic` — no CM6 imports, should pass unchanged.

For linter unit tests, mock `ITextModel`:
```ts
function mockModel(content: string) {
  const lines = content.split("\n");
  return {
    getValue: () => content,
    getPositionAt: (offset: number) => {
      let line = 1, col = 1, pos = 0;
      for (const l of lines) {
        if (pos + l.length + 1 > offset) { col = offset - pos + 1; break; }
        pos += l.length + 1; line++;
      }
      return { lineNumber: line, column: col };
    },
  } as unknown as editor.ITextModel;
}
```

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Bundle +2.5MB | Dynamic loaded, code-split via `next/dynamic` |
| y-monaco maturity | Yjs core team maintains it; test collab thoroughly |
| Workers in Next.js | `@monaco-editor/react` CDN loader or `loader.config({ monaco })` for self-host |

## Security Checklist
- [x] No `as any` casts
- [x] No `dangerouslySetInnerHTML` — N/A
- [x] localStorage validated — view mode guards preserved
- [x] Preview sandboxing — N/A (editor, not preview)

## Verification
- [ ] `make check-fe` passes
- [ ] All 9 EditorBridge methods work
- [ ] CSS + brand markers show inline
- [ ] Maizzle syntax highlighting (HTML, Liquid, MSO, YAML)
- [ ] 7 snippet completions trigger
- [ ] Dark/light theme switch
- [ ] Word wrap, Cmd+S, line/col status
- [ ] DnD design tokens
- [ ] Collab editing (cursors, sync)
- [ ] Split view code↔builder sync
- [ ] Import HTML dialog
