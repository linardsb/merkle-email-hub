"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import CodeMirror, { type ReactCodeMirrorRef } from "@uiw/react-codemirror";
import { keymap, EditorView } from "@codemirror/view";
import { Compartment } from "@codemirror/state";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { maizzleLanguage } from "./maizzle-language";
import { getEditorTheme } from "./editor-themes";
import { canIEmailLinter } from "./css-diagnostics";
import { brandLinter } from "./brand-linter";
import { EditorToolbar } from "./editor-toolbar";
import type { SaveStatus } from "../save-indicator";
import type { BrandConfig } from "@/types/brand";

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  saveStatus?: SaveStatus;
  readOnly?: boolean;
  brandConfig?: BrandConfig | null;
  onBrandViolationsChange?: (count: number) => void;
  onCursorOffsetChange?: (offset: number) => void;
}

const wrapCompartment = new Compartment();

export function CodeEditor({
  value,
  onChange,
  onSave,
  saveStatus,
  readOnly,
  brandConfig,
  onBrandViolationsChange,
  onCursorOffsetChange,
}: CodeEditorProps) {
  const { resolvedTheme } = useTheme();
  const t = useTranslations("workspace");
  const editorRef = useRef<ReactCodeMirrorRef>(null);
  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;
  const onCursorOffsetChangeRef = useRef(onCursorOffsetChange);
  onCursorOffsetChangeRef.current = onCursorOffsetChange;

  const [line, setLine] = useState(1);
  const [col, setCol] = useState(1);
  const [warningCount, setWarningCount] = useState(0);
  const [wordWrapEnabled, setWordWrapEnabled] = useState(false);

  const handleDiagnosticsChange = useCallback((count: number) => {
    setWarningCount(count);
  }, []);

  const handleBrandDiagnosticsChange = useCallback((count: number) => {
    onBrandViolationsChange?.(count);
  }, [onBrandViolationsChange]);

  const extensions = useMemo(
    () => [
      maizzleLanguage(),
      canIEmailLinter(handleDiagnosticsChange),
      ...(brandConfig ? [brandLinter(brandConfig, handleBrandDiagnosticsChange)] : []),
      keymap.of([
        {
          key: "Mod-s",
          preventDefault: true,
          run: () => {
            onSaveRef.current?.();
            return true;
          },
        },
      ]),
      wrapCompartment.of(
        wordWrapEnabled ? EditorView.lineWrapping : []
      ),
      EditorView.updateListener.of((update) => {
        const pos = update.state.selection.main.head;
        const lineInfo = update.state.doc.lineAt(pos);
        setLine(lineInfo.number);
        setCol(pos - lineInfo.from + 1);
        onCursorOffsetChangeRef.current?.(pos);
      }),
      EditorView.theme({
        "&": {
          fontFamily:
            "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, monospace",
          fontSize: "13px",
          height: "100%",
        },
        ".cm-content": {
          paddingTop: "8px",
        },
        ".cm-scroller": {
          overflow: "auto",
        },
      }),
    ],
    [handleDiagnosticsChange, handleBrandDiagnosticsChange, wordWrapEnabled, brandConfig]
  );

  const handleToggleWordWrap = useCallback(() => {
    setWordWrapEnabled((prev) => {
      const next = !prev;
      const view = editorRef.current?.view;
      if (view) {
        view.dispatch({
          effects: wrapCompartment.reconfigure(
            next ? EditorView.lineWrapping : []
          ),
        });
      }
      return next;
    });
  }, []);

  const theme = useMemo(
    () => getEditorTheme(resolvedTheme),
    [resolvedTheme]
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
      />
      <div className="relative min-h-0 flex-1">
        <div className="absolute inset-0 flex flex-col">
          <CodeMirror
            ref={editorRef}
            value={value}
            height="100%"
            style={{ height: "100%", overflow: "hidden" }}
            theme={theme}
            extensions={extensions}
            onChange={onChange}
            readOnly={readOnly}
            basicSetup={{
              lineNumbers: true,
              foldGutter: true,
              bracketMatching: true,
              closeBrackets: true,
              highlightActiveLine: true,
              highlightSelectionMatches: true,
              autocompletion: false, // We provide our own via maizzleLanguage()
              tabSize: 2,
            }}
            aria-label="Email template editor"
          />
        </div>
      </div>
    </div>
  );
}
