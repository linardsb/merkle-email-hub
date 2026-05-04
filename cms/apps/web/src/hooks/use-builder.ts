"use client";

import { useReducer, useCallback, useMemo } from "react";
import type {
  BuilderSection,
  BuilderState,
  BuilderAction,
  HistoryEntry,
} from "@/types/visual-builder";
import { assembleEmailHtml } from "@/lib/builder/html-assembler";

const MAX_HISTORY = 50;

function pushHistory(state: BuilderState): HistoryEntry[] {
  const newHistory = state.history.slice(0, state.historyIndex + 1);
  newHistory.push({
    sections: structuredClone(state.sections),
    timestamp: Date.now(),
  });
  if (newHistory.length > MAX_HISTORY) newHistory.shift();
  return newHistory;
}

function builderReducer(state: BuilderState, action: BuilderAction): BuilderState {
  switch (action.type) {
    case "ADD_SECTION": {
      const history = pushHistory(state);
      const sections = [...state.sections];
      const idx = action.atIndex ?? sections.length;
      sections.splice(idx, 0, action.section);
      return {
        ...state,
        sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "REMOVE_SECTION": {
      const history = pushHistory(state);
      const sections = state.sections.filter((s) => s.id !== action.sectionId);
      const selectedSectionId =
        state.selectedSectionId === action.sectionId ? null : state.selectedSectionId;
      return {
        ...state,
        sections,
        selectedSectionId,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "DUPLICATE_SECTION": {
      const history = pushHistory(state);
      const idx = state.sections.findIndex((s) => s.id === action.sectionId);
      if (idx === -1) return state;
      const original = state.sections[idx]!;
      const cloned = structuredClone(original);
      const duplicate: BuilderSection = {
        ...cloned,
        id: crypto.randomUUID(),
      };
      const sections = [...state.sections];
      sections.splice(idx + 1, 0, duplicate);
      return {
        ...state,
        sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "MOVE_SECTION": {
      if (action.fromIndex < 0 || action.fromIndex >= state.sections.length) return state;
      const history = pushHistory(state);
      const sections = [...state.sections];
      const [moved] = sections.splice(action.fromIndex, 1) as [BuilderSection];
      sections.splice(action.toIndex, 0, moved);
      return {
        ...state,
        sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "UPDATE_SECTION": {
      const history = pushHistory(state);
      const sections = state.sections.map((s) =>
        s.id === action.sectionId ? { ...s, ...action.updates } : s,
      );
      return {
        ...state,
        sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "SELECT_SECTION":
      return { ...state, selectedSectionId: action.sectionId };
    case "SET_SECTIONS": {
      const history = pushHistory(state);
      return {
        ...state,
        sections: action.sections,
        history,
        historyIndex: history.length - 1,
      };
    }
    case "UNDO": {
      if (state.historyIndex <= 0) return state;
      const newIndex = state.historyIndex - 1;
      return {
        ...state,
        sections: structuredClone(state.history[newIndex]!.sections),
        historyIndex: newIndex,
      };
    }
    case "REDO": {
      if (state.historyIndex >= state.history.length - 1) return state;
      const newIndex = state.historyIndex + 1;
      return {
        ...state,
        sections: structuredClone(state.history[newIndex]!.sections),
        historyIndex: newIndex,
      };
    }
    default:
      return state;
  }
}

const INITIAL_STATE: BuilderState = {
  sections: [],
  selectedSectionId: null,
  history: [{ sections: [], timestamp: Date.now() }],
  historyIndex: 0,
};

export function useBuilderState() {
  const [state, dispatch] = useReducer(builderReducer, INITIAL_STATE);

  const addSection = useCallback(
    (section: BuilderSection, atIndex?: number) =>
      dispatch({ type: "ADD_SECTION", section, atIndex }),
    [],
  );
  const removeSection = useCallback(
    (sectionId: string) => dispatch({ type: "REMOVE_SECTION", sectionId }),
    [],
  );
  const duplicateSection = useCallback(
    (sectionId: string) => dispatch({ type: "DUPLICATE_SECTION", sectionId }),
    [],
  );
  const moveSection = useCallback(
    (fromIndex: number, toIndex: number) => dispatch({ type: "MOVE_SECTION", fromIndex, toIndex }),
    [],
  );
  const updateSection = useCallback(
    (sectionId: string, updates: Partial<BuilderSection>) =>
      dispatch({ type: "UPDATE_SECTION", sectionId, updates }),
    [],
  );
  const selectSection = useCallback(
    (sectionId: string | null) => dispatch({ type: "SELECT_SECTION", sectionId }),
    [],
  );
  const setSections = useCallback(
    (sections: BuilderSection[]) => dispatch({ type: "SET_SECTIONS", sections }),
    [],
  );
  const undo = useCallback(() => dispatch({ type: "UNDO" }), []);
  const redo = useCallback(() => dispatch({ type: "REDO" }), []);

  const canUndo = state.historyIndex > 0;
  const canRedo = state.historyIndex < state.history.length - 1;

  return {
    ...state,
    addSection,
    removeSection,
    duplicateSection,
    moveSection,
    updateSection,
    selectSection,
    setSections,
    undo,
    redo,
    canUndo,
    canRedo,
  };
}

/** Memoized assembly of the email HTML preview; pure logic lives in `lib/builder/html-assembler.ts`. */
export function useBuilderPreview(
  sections: BuilderSection[],
  templateShell?: string,
): string | null {
  return useMemo(() => assembleEmailHtml(sections, templateShell), [sections, templateShell]);
}
