"use client";

import { useMemo } from "react";
import { Eye, Loader2 } from "lucide-react";
import type { Viewport } from "./preview-toolbar";

const VIEWPORT_WIDTHS: Record<Viewport, number | null> = {
  desktop: null,
  tablet: 768,
  mobile: 375,
};

const DARK_MODE_STYLE = `<style id="preview-dark-mode">
:root { color-scheme: dark !important; }
@media (prefers-color-scheme: light) {
  :root { color-scheme: dark !important; }
}
</style>`;

interface PreviewIframeProps {
  compiledHtml: string | null;
  viewport: Viewport;
  darkMode: boolean;
  zoom: number;
  isCompiling: boolean;
  viewportWidthOverride?: number | null;
}

export function PreviewIframe({
  compiledHtml,
  viewport,
  darkMode,
  zoom,
  isCompiling,
  viewportWidthOverride,
}: PreviewIframeProps) {
  const srcdoc = useMemo(() => {
    if (!compiledHtml) return null;
    if (!darkMode) return compiledHtml;

    // Inject dark mode style before </head> or prepend if no </head>
    if (compiledHtml.includes("</head>")) {
      return compiledHtml.replace("</head>", `${DARK_MODE_STYLE}\n</head>`);
    }
    return `${DARK_MODE_STYLE}\n${compiledHtml}`;
  }, [compiledHtml, darkMode]);

  const viewportWidth = viewportWidthOverride ?? VIEWPORT_WIDTHS[viewport];
  const scale = zoom / 100;

  if (!srcdoc) {
    return (
      <div className="relative flex h-full flex-col items-center justify-center bg-background p-6 text-center">
        {isCompiling ? (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">
              {"Compiling..."}
            </p>
          </>
        ) : (
          <>
            <Eye className="h-12 w-12 text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">
              {`Press ${"Ctrl+S"} to compile your template`}
            </p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="relative h-full overflow-auto bg-muted/30">
      {/* Compiling overlay */}
      {isCompiling && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Zoom container */}
      <div
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "top center",
          width: `${100 / scale}%`,
        }}
      >
        {/* Viewport container */}
        <div
          className="mx-auto"
          style={{
            maxWidth: viewportWidth ? `${viewportWidth}px` : "100%",
          }}
        >
          <iframe
            srcDoc={srcdoc}
            sandbox=""
            title="Email preview"
            className="h-[800px] w-full border-0 bg-white"
          />
        </div>
      </div>
    </div>
  );
}
