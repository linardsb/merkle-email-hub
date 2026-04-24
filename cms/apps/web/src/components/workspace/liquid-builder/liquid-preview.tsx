"use client";

import { useMemo } from "react";
import DOMPurify from "dompurify";
import { SAMPLE_DATA } from "@/lib/liquid/sample-data";

interface LiquidPreviewProps {
  code: string;
}

/**
 * Simple Liquid preview renderer.
 * Performs basic variable substitution and displays the result.
 * For demo purposes — not a full Liquid engine.
 */
export function LiquidPreview({ code }: LiquidPreviewProps) {
  const rendered = useMemo(() => {
    try {
      return simpleRender(code, SAMPLE_DATA);
    } catch {
      return code;
    }
  }, [code]);

  return (
    <div className="h-full overflow-auto border-t border-border bg-surface-elevated p-4">
      <h3 className="mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">
        {"Preview"}
      </h3>
      <div
        className="prose prose-sm max-w-none text-foreground"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(rendered) }}
      />
    </div>
  );
}

/** Basic variable substitution ({{ var }}) for preview. */
function simpleRender(code: string, data: Record<string, unknown>): string {
  return code.replace(/\{\{\s*([^}]+)\s*\}\}/g, (_match, expr: string) => {
    const path = expr.trim().split(".");
    let value: unknown = data;
    for (const key of path) {
      // hasOwnProperty.call rejects inherited keys like __proto__/constructor,
      // closing the prototype-pollution vector flagged by CodeQL.
      if (
        value &&
        typeof value === "object" &&
        Object.prototype.hasOwnProperty.call(value, key)
      ) {
        value = (value as Record<string, unknown>)[key];
      } else {
        return `{{ ${expr.trim()} }}`;
      }
    }
    return String(value ?? "");
  });
}
