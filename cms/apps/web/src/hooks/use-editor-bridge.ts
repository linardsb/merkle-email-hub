"use client";

import { useCallback, useRef, type RefObject } from "react";
import { Decoration, EditorView, type DecorationSet } from "@codemirror/view";
import { StateEffect, StateField } from "@codemirror/state";

/** Effect to set/clear highlights. */
const setHighlights = StateEffect.define<DecorationSet>();

/** StateField to store highlight decorations (added to CodeMirror extensions). */
export const highlightField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(value, tr) {
    for (const e of tr.effects) {
      if (e.is(setHighlights)) return e.value;
    }
    return value.map(tr.changes);
  },
  provide: (f) => EditorView.decorations.from(f),
});

const highlightMark = Decoration.mark({ class: "cm-token-highlight" });
const spotlightMark = Decoration.mark({ class: "cm-token-spotlight" });

/** Handle type exposed by CodeEditor via useImperativeHandle. */
export interface CodeEditorHandle {
  getView(): EditorView | null;
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

export function useEditorBridge(): EditorBridge {
  const editorRef = useRef<CodeEditorHandle | null>(null);

  const getView = useCallback((): EditorView | null => {
    return editorRef.current?.getView() ?? null;
  }, []);

  const findMatches = useCallback(
    (view: EditorView, text: string): Array<{ from: number; to: number }> => {
      const docLower = view.state.doc.toString().toLowerCase();
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
      const view = getView();
      if (!view) return;
      const pos = view.state.selection.main.head;
      view.dispatch({
        changes: { from: pos, to: pos, insert: cssText },
        selection: { anchor: pos + cssText.length },
      });
      view.focus();
    },
    [getView],
  );

  const findAndHighlight = useCallback(
    (searchText: string) => {
      const view = getView();
      if (!view) return;
      const matches = findMatches(view, searchText);
      const first = matches[0];
      if (!first) return;
      const decorations = Decoration.set(
        matches.map((m) => highlightMark.range(m.from, m.to)),
      );
      view.dispatch({
        effects: setHighlights.of(decorations),
        selection: { anchor: first.from },
        scrollIntoView: true,
      });
    },
    [getView, findMatches],
  );

  const clearHighlights = useCallback(() => {
    const view = getView();
    if (!view) return;
    view.dispatch({ effects: setHighlights.of(Decoration.none) });
  }, [getView]);

  const replaceInSelection = useCallback(
    (newHex: string) => {
      const view = getView();
      if (!view) return;
      const { from, to } = view.state.selection.main;
      if (from === to) return;
      const selectedText = view.state.sliceDoc(from, to);
      const replaced = selectedText.replace(/#[a-f\d]{6}/gi, newHex);
      if (replaced !== selectedText) {
        view.dispatch({ changes: { from, to, insert: replaced } });
      }
    },
    [getView],
  );

  const insertAtOffset = useCallback(
    (offset: number, text: string) => {
      const view = getView();
      if (!view) return;
      view.dispatch({ changes: { from: offset, to: offset, insert: text } });
      view.focus();
    },
    [getView],
  );

  const replaceAll = useCallback(
    (oldHex: string, newHex: string) => {
      const view = getView();
      if (!view) return;
      const matches = findMatches(view, oldHex);
      if (matches.length === 0) return;
      const changes = [...matches].reverse().map((m) => ({
        from: m.from,
        to: m.to,
        insert: newHex,
      }));
      view.dispatch({ changes });
    },
    [getView, findMatches],
  );

  const insertCssVariablesBlock = useCallback(
    (block: string) => {
      const view = getView();
      if (!view) return;
      const doc = view.state.doc.toString();
      const styleMatch = doc.match(/<style[^>]*>/i);
      if (styleMatch && styleMatch.index !== undefined) {
        const insertPos = styleMatch.index + styleMatch[0].length;
        view.dispatch({
          changes: { from: insertPos, to: insertPos, insert: `\n${block}\n` },
        });
      } else {
        const headMatch = doc.match(/<head[^>]*>/i);
        if (headMatch && headMatch.index !== undefined) {
          const insertPos = headMatch.index + headMatch[0].length;
          view.dispatch({
            changes: {
              from: insertPos,
              to: insertPos,
              insert: `\n<style>\n${block}\n</style>\n`,
            },
          });
        } else {
          const pos = view.state.selection.main.head;
          view.dispatch({
            changes: {
              from: pos,
              to: pos,
              insert: `<style>\n${block}\n</style>\n`,
            },
          });
        }
      }
      view.focus();
    },
    [getView],
  );

  const spotlight = useCallback(
    (searchText: string) => {
      const view = getView();
      if (!view) return;
      const matches = findMatches(view, searchText);
      if (matches.length === 0) return;
      const decorations = Decoration.set(
        matches.map((m) => spotlightMark.range(m.from, m.to)),
      );
      view.dispatch({ effects: setHighlights.of(decorations) });
    },
    [getView, findMatches],
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
