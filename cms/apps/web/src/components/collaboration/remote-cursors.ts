/**
 * Remote cursor CSS styles for y-monaco collaborative editing.
 * y-monaco renders cursors with class `.yRemoteSelection` and
 * `.yRemoteSelectionHead`. These styles are injected into the document head.
 */

const REMOTE_CURSOR_CSS = `
.yRemoteSelectionHead {
  position: relative;
  border-left: 2px solid var(--cursor-color, currentColor);
  margin-left: -1px;
  transition: all 150ms ease-out;
}
.yRemoteSelectionHead::after {
  content: attr(data-name);
  position: absolute;
  top: -1.4em;
  left: -1px;
  font-size: 10px;
  font-family: var(--font-sans, system-ui);
  line-height: 1.2;
  padding: 1px 4px;
  border-radius: 2px 2px 2px 0;
  color: white;
  background-color: var(--cursor-color, currentColor);
  white-space: nowrap;
  pointer-events: none;
  opacity: 1;
  transition: opacity 300ms ease-out;
  z-index: 10;
}
.yRemoteSelection {
  background-color: var(--cursor-color, rgba(100, 100, 255, 0.2));
  opacity: 0.25;
  transition: all 150ms ease-out;
}
`;

let injected = false;

/** Inject remote cursor styles into the document head (idempotent). */
export function injectRemoteCursorStyles(): void {
  if (injected || typeof document === "undefined") return;
  const style = document.createElement("style");
  style.textContent = REMOTE_CURSOR_CSS;
  style.setAttribute("data-remote-cursors", "");
  document.head.appendChild(style);
  injected = true;
}
