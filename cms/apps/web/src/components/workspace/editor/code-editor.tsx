"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import Editor, { type Monaco, type OnMount } from "@monaco-editor/react";
import type { editor as monacoEditor } from "monaco-editor";
import { useTheme } from "next-themes";
import {
  LANGUAGE_ID,
  monarchTokensProvider,
  languageConfiguration,
  snippetCompletions,
} from "./maizzle-language";
import { DEFAULT_LIGHT_THEME, DEFAULT_DARK_THEME, registerAllThemes } from "./editor-themes";
import { computeCssMarkers } from "./css-diagnostics";
import { computeBrandMarkers } from "./brand-linter";
import { EditorToolbar } from "./editor-toolbar";
import type { CodeEditorHandle } from "@/hooks/use-editor-bridge";
import type { SaveStatus } from "../save-indicator";
import type { BrandConfig } from "@/types/brand";
import type { Doc as YDoc } from "yjs";
import type { Awareness } from "y-protocols/awareness";
import { createCollabBinding } from "@/lib/collaboration/editor-binding";
import { injectRemoteCursorStyles } from "@/components/collaboration/remote-cursors";

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  saveStatus?: SaveStatus;
  readOnly?: boolean;
  brandConfig?: BrandConfig | null;
  onBrandViolationsChange?: (count: number) => void;
  onCursorOffsetChange?: (offset: number) => void;
  onSelectionChange?: (hasSelection: boolean) => void;
  /** When set, enables collaborative editing via Yjs CRDT */
  collaborative?: {
    doc: YDoc;
    awareness: Awareness;
    user: { name: string; color: string; role: string };
    fieldName?: string;
  };
}

let languageRegistered = false;

export const CodeEditor = forwardRef<CodeEditorHandle, CodeEditorProps>(function CodeEditor(
  {
    value,
    onChange,
    onSave,
    saveStatus,
    readOnly,
    brandConfig,
    onBrandViolationsChange,
    onCursorOffsetChange,
    onSelectionChange,
    collaborative,
  }: CodeEditorProps,
  ref,
) {
  const { resolvedTheme } = useTheme();
  const editorInstanceRef = useRef<monacoEditor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const collabDisposeRef = useRef<(() => void) | null>(null);
  const dropAbortRef = useRef<AbortController | null>(null);
  const lintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;
  const onCursorOffsetChangeRef = useRef(onCursorOffsetChange);
  onCursorOffsetChangeRef.current = onCursorOffsetChange;
  const onSelectionChangeRef = useRef(onSelectionChange);
  onSelectionChangeRef.current = onSelectionChange;
  const onBrandViolationsChangeRef = useRef(onBrandViolationsChange);
  onBrandViolationsChangeRef.current = onBrandViolationsChange;
  const brandConfigRef = useRef(brandConfig);
  brandConfigRef.current = brandConfig;

  const [line, setLine] = useState(1);
  const [col, setCol] = useState(1);
  const [warningCount, setWarningCount] = useState(0);
  const [wordWrapEnabled, setWordWrapEnabled] = useState(false);
  const defaultThemeId = resolvedTheme === "dark" ? DEFAULT_DARK_THEME : DEFAULT_LIGHT_THEME;
  const [editorThemeId, setEditorThemeId] = useState(defaultThemeId);

  useImperativeHandle(ref, () => ({
    getEditor() {
      return editorInstanceRef.current;
    },
  }));

  const themeId = editorThemeId;

  const runLinters = useCallback((editor: monacoEditor.IStandaloneCodeEditor, monaco: Monaco) => {
    const model = editor.getModel();
    if (!model) return;
    const cssMarkers = computeCssMarkers(model);
    const brandMarkers = brandConfigRef.current
      ? computeBrandMarkers(model, brandConfigRef.current)
      : [];
    monaco.editor.setModelMarkers(model, "css-diagnostics", cssMarkers);
    monaco.editor.setModelMarkers(model, "brand-linter", brandMarkers);
    setWarningCount(cssMarkers.length);
    onBrandViolationsChangeRef.current?.(brandMarkers.length);
  }, []);

  const debouncedLint = useCallback(
    (editor: monacoEditor.IStandaloneCodeEditor, monaco: Monaco) => {
      if (lintTimerRef.current) clearTimeout(lintTimerRef.current);
      lintTimerRef.current = setTimeout(() => runLinters(editor, monaco), 300);
    },
    [runLinters],
  );

  const handleEditorDidMount: OnMount = useCallback(
    (editor, monaco) => {
      editorInstanceRef.current = editor;
      monacoRef.current = monaco;

      // Register language, themes, and completions once
      if (!languageRegistered) {
        monaco.languages.register({ id: LANGUAGE_ID });
        monaco.languages.setMonarchTokensProvider(LANGUAGE_ID, monarchTokensProvider);
        monaco.languages.setLanguageConfiguration(LANGUAGE_ID, languageConfiguration);

        monaco.languages.registerCompletionItemProvider(LANGUAGE_ID, {
          provideCompletionItems: (
            model: monacoEditor.ITextModel,
            position: { lineNumber: number; column: number },
          ) => {
            const word = model.getWordUntilPosition(position);
            const range = {
              startLineNumber: position.lineNumber,
              startColumn: word.startColumn,
              endLineNumber: position.lineNumber,
              endColumn: word.endColumn,
            };
            return {
              suggestions: snippetCompletions.map((s) => ({
                label: s.label,
                kind: monaco.languages.CompletionItemKind.Snippet,
                insertText: s.insertText,
                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                detail: s.detail,
                range,
              })),
            };
          },
        });

        registerAllThemes(monaco);
        languageRegistered = true;
      }

      monaco.editor.setTheme(themeId);

      // Cmd/Ctrl+S
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        onSaveRef.current?.();
      });

      // Cursor position tracking
      editor.onDidChangeCursorPosition((e) => {
        setLine(e.position.lineNumber);
        setCol(e.position.column);
        const model = editor.getModel();
        if (model) {
          onCursorOffsetChangeRef.current?.(model.getOffsetAt(e.position));
        }
      });

      // Selection tracking
      editor.onDidChangeCursorSelection((e) => {
        const sel = e.selection;
        onSelectionChangeRef.current?.(
          sel.startLineNumber !== sel.endLineNumber || sel.startColumn !== sel.endColumn,
        );
      });

      // Lint on content change (debounced)
      editor.onDidChangeModelContent(() => {
        debouncedLint(editor, monaco);
      });

      // DnD for design tokens — with cleanup via AbortController
      const domNode = editor.getDomNode();
      if (domNode) {
        dropAbortRef.current?.abort();
        const controller = new AbortController();
        dropAbortRef.current = controller;
        domNode.addEventListener(
          "drop",
          (event: DragEvent) => {
            const tokenData = event.dataTransfer?.getData("application/x-design-token");
            if (tokenData) {
              event.preventDefault();
              const target = editor.getTargetAtClientPoint(event.clientX, event.clientY);
              if (target?.position) {
                editor.executeEdits("design-token-drop", [
                  {
                    range: {
                      startLineNumber: target.position.lineNumber,
                      startColumn: target.position.column,
                      endLineNumber: target.position.lineNumber,
                      endColumn: target.position.column,
                    },
                    text: `color: ${tokenData};`,
                  },
                ]);
              }
            }
          },
          { signal: controller.signal },
        );
      }

      // Remeasure fonts after web fonts load — prevents line overlap
      document.fonts.ready.then(() => {
        monaco.editor.remeasureFonts();
      });

      // Initial lint
      runLinters(editor, monaco);

      // Collaborative binding
      if (collaborative) {
        injectRemoteCursorStyles();
        try {
          const binding = createCollabBinding(
            {
              doc: collaborative.doc,
              awareness: collaborative.awareness,
              user: collaborative.user,
              fieldName: collaborative.fieldName,
            },
            editor,
          );
          collabDisposeRef.current = binding.dispose;
        } catch (err) {
          console.warn(
            "[CodeEditor] Collaborative binding failed, falling back to solo mode:",
            err,
          );
        }
      }
    },
    [themeId, collaborative, debouncedLint, runLinters],
  );

  // Clean up collab binding + drop listener on unmount
  useEffect(() => {
    return () => {
      collabDisposeRef.current?.();
      collabDisposeRef.current = null;
      dropAbortRef.current?.abort();
      dropAbortRef.current = null;
    };
  }, []);

  // Re-apply theme on resolvedTheme change
  useEffect(() => {
    const monaco = monacoRef.current;
    if (monaco) {
      monaco.editor.setTheme(themeId);
    }
  }, [themeId]);

  // Re-run linters when brandConfig changes
  useEffect(() => {
    const editor = editorInstanceRef.current;
    const monaco = monacoRef.current;
    if (editor && monaco) {
      runLinters(editor, monaco);
    }
  }, [brandConfig, runLinters]);

  const handleEditorThemeChange = useCallback((newThemeId: string) => {
    setEditorThemeId(newThemeId);
    const monaco = monacoRef.current;
    if (monaco) {
      monaco.editor.setTheme(newThemeId);
    }
  }, []);

  const handleToggleWordWrap = useCallback(() => {
    setWordWrapEnabled((prev) => {
      const next = !prev;
      editorInstanceRef.current?.updateOptions({ wordWrap: next ? "on" : "off" });
      return next;
    });
  }, []);

  const handleChange = useCallback(
    (val: string | undefined) => {
      if (val !== undefined) onChange(val);
    },
    [onChange],
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <EditorToolbar
        line={line}
        col={col}
        warningCount={warningCount}
        wordWrapEnabled={wordWrapEnabled}
        saveStatus={saveStatus ?? "idle"}
        onToggleWordWrap={handleToggleWordWrap}
        editorThemeId={editorThemeId}
        onEditorThemeChange={handleEditorThemeChange}
      />
      <div className="relative min-h-0 flex-1">
        <div className="absolute inset-0">
          <Editor
            height="100%"
            language={LANGUAGE_ID}
            theme={themeId}
            value={collaborative ? undefined : value}
            onChange={collaborative ? undefined : handleChange}
            onMount={handleEditorDidMount}
            options={{
              readOnly,
              fontSize: 13,
              fontFamily:
                "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, monospace",
              tabSize: 2,
              minimap: { enabled: true },
              lineNumbers: "on",
              folding: true,
              bracketPairColorization: { enabled: true },
              matchBrackets: "always",
              autoClosingBrackets: "always",
              renderLineHighlight: "line",
              scrollBeyondLastLine: false,
              wordWrap: wordWrapEnabled ? "on" : "off",
              padding: { top: 8 },
              automaticLayout: true,
              scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
            }}
          />
        </div>
      </div>
    </div>
  );
});
