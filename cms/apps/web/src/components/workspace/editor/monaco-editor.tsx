"use client";

import { useCallback, useRef, useState } from "react";
import Editor, { type BeforeMount, type OnMount } from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { registerMaizzleLanguage } from "./maizzle-language";
import { defineEditorThemes, getEditorTheme } from "./monaco-theme";
import { runCssDiagnostics, getDiagnosticCount } from "./css-diagnostics";
import { EditorToolbar } from "./editor-toolbar";
import type { SaveStatus } from "../save-indicator";

interface MonacoEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  saveStatus?: SaveStatus;
  readOnly?: boolean;
}

export function MonacoEditor({ value, onChange, onSave, saveStatus, readOnly }: MonacoEditorProps) {
  const { resolvedTheme } = useTheme();
  const t = useTranslations("workspace");
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof Monaco | null>(null);
  const diagnosticsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;

  const [line, setLine] = useState(1);
  const [col, setCol] = useState(1);
  const [warningCount, setWarningCount] = useState(0);
  const [minimapEnabled, setMinimapEnabled] = useState(true);
  const [wordWrapEnabled, setWordWrapEnabled] = useState(false);

  const handleBeforeMount: BeforeMount = useCallback((monaco) => {
    registerMaizzleLanguage(monaco);
    defineEditorThemes(monaco);
  }, []);

  const updateDiagnostics = useCallback(() => {
    const monaco = monacoRef.current;
    const editor = editorRef.current;
    if (!monaco || !editor) return;
    const model = editor.getModel();
    if (!model) return;
    runCssDiagnostics(monaco, model);
    setWarningCount(getDiagnosticCount(monaco, model));
  }, []);

  const handleMount: OnMount = useCallback(
    (editor, monaco) => {
      editorRef.current = editor;
      monacoRef.current = monaco;

      editor.onDidChangeCursorPosition((e) => {
        setLine(e.position.lineNumber);
        setCol(e.position.column);
      });

      updateDiagnostics();
      editor.focus();

      // Ctrl+S / Cmd+S to save
      editor.addCommand(
        monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
        () => onSaveRef.current?.()
      );
    },
    [updateDiagnostics]
  );

  const handleChange = useCallback(
    (newValue: string | undefined) => {
      onChange(newValue ?? "");

      if (diagnosticsTimerRef.current) {
        clearTimeout(diagnosticsTimerRef.current);
      }
      diagnosticsTimerRef.current = setTimeout(updateDiagnostics, 300);
    },
    [onChange, updateDiagnostics]
  );

  const handleToggleMinimap = useCallback(() => {
    setMinimapEnabled((prev) => {
      const next = !prev;
      editorRef.current?.updateOptions({ minimap: { enabled: next } });
      return next;
    });
  }, []);

  const handleToggleWordWrap = useCallback(() => {
    setWordWrapEnabled((prev) => {
      const next = !prev;
      editorRef.current?.updateOptions({
        wordWrap: next ? "on" : "off",
      });
      return next;
    });
  }, []);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <EditorToolbar
        line={line}
        col={col}
        warningCount={warningCount}
        minimapEnabled={minimapEnabled}
        wordWrapEnabled={wordWrapEnabled}
        saveStatus={saveStatus ?? "idle"}
        onToggleMinimap={handleToggleMinimap}
        onToggleWordWrap={handleToggleWordWrap}
      />
      <div className="flex-1">
        <Editor
          language="maizzle"
          theme={getEditorTheme(resolvedTheme)}
          value={value}
          onChange={handleChange}
          beforeMount={handleBeforeMount}
          onMount={handleMount}
          loading={
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              {t("editorLoading")}
            </div>
          }
          options={{
            readOnly,
            fontSize: 13,
            fontFamily:
              "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, monospace",
            minimap: { enabled: minimapEnabled },
            wordWrap: wordWrapEnabled ? "on" : "off",
            bracketPairColorization: { enabled: true },
            autoClosingBrackets: "always",
            folding: true,
            matchBrackets: "always",
            scrollBeyondLastLine: false,
            smoothScrolling: true,
            padding: { top: 8 },
            ariaLabel: "Email template editor",
            renderWhitespace: "selection",
            tabSize: 2,
            lineNumbers: "on",
            glyphMargin: false,
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
}
