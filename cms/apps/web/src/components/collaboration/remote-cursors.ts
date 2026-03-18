import { EditorView } from "@codemirror/view";

/**
 * CodeMirror theme extension for enhanced remote cursor styling.
 * y-codemirror.next renders cursors with class `.yRemoteSelection` and
 * `.yRemoteSelectionHead`. This extension styles them with labels and animation.
 */
export function remoteCursorStyles() {
  return EditorView.theme({
    // Remote cursor line — thin colored bar
    ".yRemoteSelectionHead": {
      position: "relative",
      borderLeft: "2px solid var(--cursor-color, currentColor)",
      marginLeft: "-1px",
      transition: "all 150ms ease-out",
    },
    // Cursor name label
    ".yRemoteSelectionHead::after": {
      content: "attr(data-name)",
      position: "absolute",
      top: "-1.4em",
      left: "-1px",
      fontSize: "10px",
      fontFamily: "var(--font-sans, system-ui)",
      lineHeight: "1.2",
      padding: "1px 4px",
      borderRadius: "2px 2px 2px 0",
      color: "white",
      backgroundColor: "var(--cursor-color, currentColor)",
      whiteSpace: "nowrap",
      pointerEvents: "none",
      opacity: "1",
      transition: "opacity 300ms ease-out",
      zIndex: "10",
    },
    // Selection highlight — semi-transparent background
    ".yRemoteSelection": {
      backgroundColor: "var(--cursor-color, rgba(100, 100, 255, 0.2))",
      opacity: "0.25",
      transition: "all 150ms ease-out",
    },
  });
}
