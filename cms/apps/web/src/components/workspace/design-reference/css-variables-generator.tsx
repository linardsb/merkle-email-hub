"use client";

import { Code2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@email-hub/ui/components/ui/button";
import { generateCssVariablesBlock } from "@/lib/color-utils";
import type { DesignTokens } from "@/types/design-sync";
import type { EditorBridge } from "@/hooks/use-editor-bridge";

interface CssVariablesGeneratorProps {
  tokens: DesignTokens;
  editor: EditorBridge;
}

export function CssVariablesGenerator({ tokens, editor }: CssVariablesGeneratorProps) {
  const handleGenerate = () => {
    const block = generateCssVariablesBlock(tokens.colors, tokens.typography);
    editor.insertCssVariablesBlock(block);
    toast.success("CSS variables inserted into <style>");
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleGenerate}
      className="h-7 gap-1.5 text-xs"
    >
      <Code2 className="h-3.5 w-3.5" />
      {"Generate CSS Variables"}
    </Button>
  );
}
