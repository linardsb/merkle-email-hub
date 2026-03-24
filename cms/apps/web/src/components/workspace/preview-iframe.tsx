"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { Eye, Loader2 } from "lucide-react";
import type { Viewport } from "./preview-toolbar";
import { ensureDarkModeContrast } from "@/lib/dark-mode-contrast";

const VIEWPORT_WIDTHS: Record<Viewport, number | null> = {
  desktop: null,
  tablet: 768,
  mobile: 375,
};

const DARK_MODE_META = `<meta name="color-scheme" content="dark">`;
const DARK_MODE_STYLE = `<style id="preview-dark-mode">
:root { color-scheme: dark !important; }
@media (prefers-color-scheme: light) {
  :root { color-scheme: dark !important; }
}
body { background-color: #121212 !important; }
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

    // Fix dark-on-dark text visibility before injecting dark mode styles
    const safeHtml = ensureDarkModeContrast(compiledHtml);

    // Inject dark mode meta + style to trigger @media (prefers-color-scheme: dark) in email HTML
    if (safeHtml.includes("</head>")) {
      return safeHtml.replace(
        "</head>",
        `${DARK_MODE_META}\n${DARK_MODE_STYLE}\n</head>`,
      );
    }
    if (safeHtml.includes("<head>")) {
      return safeHtml.replace(
        "<head>",
        `<head>\n${DARK_MODE_META}\n${DARK_MODE_STYLE}`,
      );
    }
    return `${DARK_MODE_META}\n${DARK_MODE_STYLE}\n${safeHtml}`;
  }, [compiledHtml, darkMode]);

  const viewportWidth = viewportWidthOverride ?? VIEWPORT_WIDTHS[viewport];
  const scale = zoom / 100;
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [iframeHeight, setIframeHeight] = useState(800);

  const handleLoad = useCallback(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    try {
      const doc = iframe.contentDocument;
      if (doc?.body) {
        const h = doc.documentElement.scrollHeight;
        if (h > 0) setIframeHeight(h);
      }
    } catch {
      // sandboxed — keep default height
    }
  }, []);

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

  const bgClass = darkMode ? "bg-[#121212]" : "bg-white";

  return (
    <div className={`relative flex h-full min-h-0 flex-col overflow-auto ${bgClass}`}>
      {/* Compiling overlay */}
      {isCompiling && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Zoom container */}
      <div
        className="flex-1"
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "top center",
          width: `${100 / scale}%`,
        }}
      >
        {/* Viewport container */}
        <div
          className="mx-auto h-full"
          style={{
            maxWidth: viewportWidth ? `${viewportWidth}px` : "100%",
          }}
        >
          <iframe
            ref={iframeRef}
            srcDoc={srcdoc}
            sandbox="allow-same-origin"
            title="Email preview"
            onLoad={handleLoad}
            style={{ minHeight: `${iframeHeight}px` }}
            className={`h-full w-full border-0 ${bgClass}`}
          />
        </div>
      </div>
    </div>
  );
}
