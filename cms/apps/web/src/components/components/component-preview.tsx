"use client";

import { useMemo } from "react";
import { Eye } from "../icons";

const DARK_MODE_META = `<meta name="color-scheme" content="dark">`;
const DARK_MODE_STYLE = `<style id="component-dark-mode">
:root { color-scheme: dark !important; }
@media (prefers-color-scheme: light) {
  :root { color-scheme: dark !important; }
}
body { background-color: #121212 !important; }
</style>`;

interface ComponentPreviewProps {
  html: string | null;
  darkMode?: boolean;
  height?: number;
  interactive?: boolean;
}

export function ComponentPreview({
  html,
  darkMode = false,
  height = 300,
  interactive = false,
}: ComponentPreviewProps) {
  const srcdoc = useMemo(() => {
    if (!html) return null;
    if (!darkMode) return html;

    if (html.includes("</head>")) {
      return html.replace("</head>", `${DARK_MODE_META}\n${DARK_MODE_STYLE}\n</head>`);
    }
    if (html.includes("<head>")) {
      return html.replace("<head>", `<head>\n${DARK_MODE_META}\n${DARK_MODE_STYLE}`);
    }
    return `${DARK_MODE_META}\n${DARK_MODE_STYLE}\n${html}`;
  }, [html, darkMode]);

  if (!srcdoc) {
    return (
      <div
        className="bg-surface-muted flex flex-col items-center justify-center text-center"
        style={{ height: `${height}px` }}
      >
        <Eye className="text-foreground-muted h-8 w-8" />
        <p className="text-foreground-muted mt-2 text-xs">{"No source available"}</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-muted overflow-hidden" style={{ height: `${height}px` }}>
      <iframe
        srcDoc={srcdoc}
        sandbox="allow-same-origin"
        title={"Preview"}
        className={`h-full w-full border-0 ${darkMode ? "bg-[#121212]" : "bg-white"}`}
        style={{ pointerEvents: interactive ? "auto" : "none" }}
      />
    </div>
  );
}
