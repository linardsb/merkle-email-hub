"use client";

import { useCallback, useRef, type RefObject } from "react";
import type { editor as monacoEditor } from "monaco-editor";

/** Handle type exposed by CodeEditor via useImperativeHandle. */
export interface CodeEditorHandle {
  getEditor(): monacoEditor.IStandaloneCodeEditor | null;
}

export interface EditorBridge {
  /** #1 -- Insert CSS declaration at current cursor position. */
  insertAtCursor: (cssText: string) => void;
  /** #2 -- Find and highlight all occurrences of a string in the editor. */
  findAndHighlight: (searchText: string) => void;
  /** Clear all highlights set by findAndHighlight or spotlight. */
  clearHighlights: () => void;
  /** #3 -- Replace all hex color values in the current selection with newHex. */
  replaceInSelection: (newHex: string) => void;
  /** #6 -- Insert text at a specific offset (for drag-and-drop). */
  insertAtOffset: (offset: number, text: string) => void;
  /** #7 -- Replace all occurrences of a hex in the entire document. */
  replaceAll: (oldHex: string, newHex: string) => void;
  /** #8 -- Insert a CSS variables block into the <style> section. */
  insertCssVariablesBlock: (block: string) => void;
  /** #9 -- Spotlight (hover highlight) all occurrences -- non-destructive. */
  spotlight: (searchText: string) => void;
  /** Ref to attach to the CodeEditor. */
  editorRef: RefObject<CodeEditorHandle | null>;
}

/** Module-level decoration IDs for deltaDecorations. */
let activeDecorations: string[] = [];

export function useEditorBridge(): EditorBridge {
  const editorRef = useRef<CodeEditorHandle | null>(null);

  const getEditor = useCallback((): monacoEditor.IStandaloneCodeEditor | null => {
    return editorRef.current?.getEditor() ?? null;
  }, []);

  const findMatches = useCallback(
    (editor: monacoEditor.IStandaloneCodeEditor, text: string): Array<{ from: number; to: number }> => {
      const model = editor.getModel();
      if (!model) return [];
      const docLower = model.getValue().toLowerCase();
      const lower = text.toLowerCase();
      const matches: Array<{ from: number; to: number }> = [];
      let idx = 0;
      while (true) {
        idx = docLower.indexOf(lower, idx);
        if (idx === -1) break;
        matches.push({ from: idx, to: idx + text.length });
        idx += text.length;
      }
      return matches;
    },
    [],
  );

  const insertAtCursor = useCallback(
    (cssText: string) => {
      const editor = getEditor();
      if (!editor) return;
      const position = editor.getPosition();
      if (!position) return;
      editor.executeEdits("editor-bridge", [{
        range: {
          startLineNumber: position.lineNumber, startColumn: position.column,
          endLineNumber: position.lineNumber, endColumn: position.column,
        },
        text: cssText,
      }]);
      editor.focus();
    },
    [getEditor],
  );

  const findAndHighlight = useCallback(
    (searchText: string) => {
      const editor = getEditor();
      if (!editor) return;
      const model = editor.getModel();
      if (!model) return;
      const matches = findMatches(editor, searchText);
      const first = matches[0];
      if (!first) return;
      const decorations = matches.map((m) => {
        const startPos = model.getPositionAt(m.from);
        const endPos = model.getPositionAt(m.to);
        return {
          range: {
            startLineNumber: startPos.lineNumber, startColumn: startPos.column,
            endLineNumber: endPos.lineNumber, endColumn: endPos.column,
          },
          options: { className: "monaco-token-highlight" },
        };
      });
      activeDecorations = editor.deltaDecorations(activeDecorations, decorations);
      const firstPos = model.getPositionAt(first.from);
      editor.revealPositionInCenter(firstPos);
    },
    [getEditor, findMatches],
  );

  const clearHighlights = useCallback(() => {
    const editor = getEditor();
    if (!editor) return;
    activeDecorations = editor.deltaDecorations(activeDecorations, []);
  }, [getEditor]);

  const replaceInSelection = useCallback(
    (newHex: string) => {
      const editor = getEditor();
      if (!editor) return;
      const model = editor.getModel();
      const selection = editor.getSelection();
      if (!model || !selection || selection.isEmpty()) return;
      const selectedText = model.getValueInRange(selection);
      const replaced = selectedText.replace(/#[a-f\d]{6}/gi, newHex);
      if (replaced !== selectedText) {
        editor.executeEdits("editor-bridge", [{ range: selection, text: replaced }]);
      }
    },
    [getEditor],
  );

  const insertAtOffset = useCallback(
    (offset: number, text: string) => {
      const editor = getEditor();
      if (!editor) return;
      const model = editor.getModel();
      if (!model) return;
      const position = model.getPositionAt(offset);
      editor.executeEdits("editor-bridge", [{
        range: {
          startLineNumber: position.lineNumber, startColumn: position.column,
          endLineNumber: position.lineNumber, endColumn: position.column,
        },
        text,
      }]);
      editor.focus();
    },
    [getEditor],
  );

  const replaceAll = useCallback(
    (oldHex: string, newHex: string) => {
      const editor = getEditor();
      if (!editor) return;
      const matches = findMatches(editor, oldHex);
      if (matches.length === 0) return;
      const model = editor.getModel();
      if (!model) return;
      const edits = [...matches].reverse().map((m) => {
        const startPos = model.getPositionAt(m.from);
        const endPos = model.getPositionAt(m.to);
        return {
          range: {
            startLineNumber: startPos.lineNumber, startColumn: startPos.column,
            endLineNumber: endPos.lineNumber, endColumn: endPos.column,
          },
          text: newHex,
        };
      });
      editor.executeEdits("editor-bridge", edits);
    },
    [getEditor, findMatches],
  );

  const insertCssVariablesBlock = useCallback(
    (block: string) => {
      const editor = getEditor();
      if (!editor) return;
      const model = editor.getModel();
      if (!model) return;
      const doc = model.getValue();
      const styleMatch = doc.match(/<style[^>]*>/i);
      if (styleMatch && styleMatch.index !== undefined) {
        const insertOffset = styleMatch.index + styleMatch[0].length;
        const pos = model.getPositionAt(insertOffset);
        editor.executeEdits("editor-bridge", [{
          range: {
            startLineNumber: pos.lineNumber, startColumn: pos.column,
            endLineNumber: pos.lineNumber, endColumn: pos.column,
          },
          text: `\n${block}\n`,
        }]);
      } else {
        const headMatch = doc.match(/<head[^>]*>/i);
        if (headMatch && headMatch.index !== undefined) {
          const insertOffset = headMatch.index + headMatch[0].length;
          const pos = model.getPositionAt(insertOffset);
          editor.executeEdits("editor-bridge", [{
            range: {
              startLineNumber: pos.lineNumber, startColumn: pos.column,
              endLineNumber: pos.lineNumber, endColumn: pos.column,
            },
            text: `\n<style>\n${block}\n</style>\n`,
          }]);
        } else {
          const position = editor.getPosition();
          if (!position) return;
          editor.executeEdits("editor-bridge", [{
            range: {
              startLineNumber: position.lineNumber, startColumn: position.column,
              endLineNumber: position.lineNumber, endColumn: position.column,
            },
            text: `<style>\n${block}\n</style>\n`,
          }]);
        }
      }
      editor.focus();
    },
    [getEditor],
  );

  const spotlight = useCallback(
    (searchText: string) => {
      const editor = getEditor();
      if (!editor) return;
      const model = editor.getModel();
      if (!model) return;
      const matches = findMatches(editor, searchText);
      if (matches.length === 0) return;
      const decorations = matches.map((m) => {
        const startPos = model.getPositionAt(m.from);
        const endPos = model.getPositionAt(m.to);
        return {
          range: {
            startLineNumber: startPos.lineNumber, startColumn: startPos.column,
            endLineNumber: endPos.lineNumber, endColumn: endPos.column,
          },
          options: { className: "monaco-token-spotlight" },
        };
      });
      activeDecorations = editor.deltaDecorations(activeDecorations, decorations);
    },
    [getEditor, findMatches],
  );

  return {
    insertAtCursor,
    findAndHighlight,
    clearHighlights,
    replaceInSelection,
    insertAtOffset,
    replaceAll,
    insertCssVariablesBlock,
    spotlight,
    editorRef,
  };
}
