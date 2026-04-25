"use client";

import { useState } from "react";
import { Moon, Sun, Monitor, Tablet, Smartphone, Eye } from "../icons";

type Viewport = "desktop" | "tablet" | "mobile";

const VIEWPORT_WIDTHS: Record<Viewport, string> = {
  desktop: "100%",
  tablet: "768px",
  mobile: "375px",
};

const DARK_MODE_STYLE = `<style id="approval-dark-mode">
:root { color-scheme: dark !important; }
@media (prefers-color-scheme: light) {
  :root { color-scheme: dark !important; }
}
</style>`;

interface ApprovalPreviewProps {
  compiledHtml: string | null;
}

export function ApprovalPreview({ compiledHtml }: ApprovalPreviewProps) {
  const [darkMode, setDarkMode] = useState(false);
  const [viewport, setViewport] = useState<Viewport>("desktop");

  if (!compiledHtml) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center">
        <Eye className="text-foreground-muted h-8 w-8" />
        <p className="text-foreground-muted mt-2 text-sm">
          {"No compiled HTML available for preview"}
        </p>
      </div>
    );
  }

  const htmlWithDarkMode = darkMode
    ? compiledHtml.replace("</head>", `${DARK_MODE_STYLE}</head>`)
    : compiledHtml;

  const viewportIcons: Record<Viewport, typeof Monitor> = {
    desktop: Monitor,
    tablet: Tablet,
    mobile: Smartphone,
  };

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="border-border flex items-center justify-between border-b px-3 py-2">
        <div className="flex items-center gap-1">
          {(["desktop", "tablet", "mobile"] as Viewport[]).map((vp) => {
            const Icon = viewportIcons[vp];
            return (
              <button
                key={vp}
                type="button"
                onClick={() => setViewport(vp)}
                aria-label={vp}
                className={`rounded p-1.5 transition-colors ${
                  viewport === vp
                    ? "bg-interactive text-foreground-inverse"
                    : "text-foreground-muted hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => setDarkMode(!darkMode)}
          className="text-foreground-muted hover:text-foreground rounded p-1.5 transition-colors"
          title={"Toggle dark mode"}
          aria-label={"Toggle dark mode"}
        >
          {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>

      {/* Preview iframe */}
      <div className="bg-surface-muted flex-1 overflow-auto p-4">
        <div className="bg-surface mx-auto" style={{ maxWidth: VIEWPORT_WIDTHS[viewport] }}>
          <iframe
            srcDoc={htmlWithDarkMode}
            sandbox="allow-same-origin"
            title={"Preview"}
            className="h-[800px] w-full border-0"
          />
        </div>
      </div>
    </div>
  );
}
