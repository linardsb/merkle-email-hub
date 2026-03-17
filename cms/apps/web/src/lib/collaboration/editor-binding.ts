/**
 * Yjs <-> CodeMirror 6 binding for collaborative editing.
 * Wraps y-codemirror.next with Hub-specific configuration.
 */
import * as Y from "yjs";
import { yCollab } from "y-codemirror.next";
import type { Extension } from "@codemirror/state";
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
 * Creates a CodeMirror extension for collaborative editing.
 *
 * This replaces CodeMirror's built-in undo/redo with Y.UndoManager
 * which tracks per-user operations for collaborative undo.
 */
export function createCollabExtension(
  config: CollaborativeEditorConfig,
): Extension {
  const { doc, awareness, user, fieldName = "content" } = config;

  // Get or create the shared Y.Text type
  const ytext = doc.getText(fieldName);

  // Set local user awareness
  setLocalUser(awareness, user);

  // Create undo manager scoped to this user's operations
  const undoManager = new Y.UndoManager(ytext);

  // y-codemirror.next provides:
  // - Two-way binding between Y.Text and CodeMirror
  // - Remote cursor decorations (colored cursors for each peer)
  // - Integration with Y.UndoManager for collaborative undo/redo
  return yCollab(ytext, awareness, { undoManager });
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
export function initDocumentContent(
  doc: Y.Doc,
  content: string,
  fieldName = "content",
): void {
  const ytext = doc.getText(fieldName);
  if (ytext.length === 0) {
    ytext.insert(0, content);
  }
}
