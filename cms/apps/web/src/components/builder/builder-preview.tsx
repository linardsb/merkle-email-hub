"use client";

import { Mail } from "lucide-react";

interface BuilderPreviewProps {
  assembledHtml: string | null;
  zoom: number;
}

export function BuilderPreview({ assembledHtml, zoom }: BuilderPreviewProps) {
  const scale = zoom / 100;

  if (!assembledHtml) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
        <Mail className="h-10 w-10 opacity-40" />
        <p className="text-sm">
          {"Add sections from the palette to preview your email"}
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full justify-center overflow-auto bg-muted/30 p-4">
      <div
        className="origin-top"
        style={{
          width: 600,
          transform: `scale(${scale})`,
        }}
      >
        <iframe
          title="Email preview"
          srcDoc={assembledHtml}
          sandbox=""
          className="w-full border border-border bg-white"
          style={{ minHeight: 600, pointerEvents: "none" }}
        />
      </div>
    </div>
  );
}
