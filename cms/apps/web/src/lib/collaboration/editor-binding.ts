/**
 * Yjs <-> Monaco Editor binding for collaborative editing.
 * Wraps y-monaco with Hub-specific configuration.
 */
import * as Y from "yjs";
import { MonacoBinding } from "y-monaco";
import type { editor as monacoEditor } from "monaco-editor";
import type { Awareness } from "y-protocols/awareness";
import type { CollabUser } from "./awareness";
import { setLocalUser } from "./awareness";

export interface CollaborativeEditorConfig {
  /** Yjs document */
  doc: Y.Doc;
  /** Yjs Awareness instance (from WebsocketProvider) */
  awareness: Awareness;
  /** Local user info for cursor display */
  user: CollabUser;
  /** Name of the Y.Text field in the doc (default: "content") */
  fieldName?: string;
}

/**
 * Creates a y-monaco binding for collaborative editing.
 *
 * y-monaco manages two-way sync between Y.Text and the Monaco model,
 * remote cursor decorations, and undo/redo via Y.UndoManager.
 */
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

/**
 * Get the current document content from a Y.Text field.
 * Useful for read-only access or save operations.
 */
export function getDocumentContent(doc: Y.Doc, fieldName = "content"): string {
  return doc.getText(fieldName).toString();
}

/**
 * Initialize a Y.Doc with content (for first-time setup).
 * Only call this once when creating a new collaborative document.
 */
export function initDocumentContent(doc: Y.Doc, content: string, fieldName = "content"): void {
  const ytext = doc.getText(fieldName);
  if (ytext.length === 0) {
    ytext.insert(0, content);
  }
}
