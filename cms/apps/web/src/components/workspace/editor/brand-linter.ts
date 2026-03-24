import type { editor } from "monaco-editor";
import type { BrandConfig } from "@/types/brand";

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function computeBrandMarkers(model: editor.ITextModel, config: BrandConfig): editor.IMarkerData[] {
  const content = model.getValue();
  const markers: editor.IMarkerData[] = [];
  const approvedHexes = new Set(config.colors.map((c) => c.hex.toLowerCase()));
  const approvedFonts = new Set(
    config.typography.map((t) => t.family.toLowerCase())
  );

  // Check for off-brand hex colors in CSS
  const colorPattern = /(?:color|background(?:-color)?)\s*:\s*(#[0-9a-fA-F]{3,8})/gi;
  let match: RegExpExecArray | null;
  while ((match = colorPattern.exec(content)) !== null) {
    const hex = match[1]!.toLowerCase();
    const normalized =
      hex.length === 4
        ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
        : hex;
    if (!approvedHexes.has(normalized)) {
      const startPos = model.getPositionAt(match.index);
      const endPos = model.getPositionAt(match.index + match[0].length);
      markers.push({
        severity: 4, // MarkerSeverity.Warning
        message: `Off-brand color ${hex}. Approved colors: ${config.colors.map((c) => `${c.name} (${c.hex})`).join(", ")}`,
        source: "Brand",
        startLineNumber: startPos.lineNumber, startColumn: startPos.column,
        endLineNumber: endPos.lineNumber, endColumn: endPos.column,
      });
    }
  }

  // Check for off-brand fonts
  const fontPattern = /font-family\s*:\s*['"]?([^'",;}\n]+)/gi;
  while ((match = fontPattern.exec(content)) !== null) {
    const font = match[1]!.trim().toLowerCase();
    const isApproved = Array.from(approvedFonts).some(
      (approved) => font.includes(approved)
    );
    if (!isApproved && font !== "inherit" && font !== "initial") {
      const startPos = model.getPositionAt(match.index);
      const endPos = model.getPositionAt(match.index + match[0].length);
      markers.push({
        severity: 4, // MarkerSeverity.Warning
        message: `Off-brand font "${match[1]!.trim()}". Approved fonts: ${config.typography.map((t) => t.family).join(", ")}`,
        source: "Brand",
        startLineNumber: startPos.lineNumber, startColumn: startPos.column,
        endLineNumber: endPos.lineNumber, endColumn: endPos.column,
      });
    }
  }

  // Check forbidden patterns (config is admin-defined BrandConfig, not user input)
  // nosemgrep: javascript.lang.security.audit.prototype-pollution.prototype-pollution-loop.prototype-pollution-loop
  for (const fp of config.forbiddenPatterns) {
    try {
      // nosemgrep: javascript.lang.security.audit.detect-non-literal-regexp.detect-non-literal-regexp
      const regex = new RegExp(fp.pattern, "gi");
      while ((match = regex.exec(content)) !== null) {
        const startPos = model.getPositionAt(match.index);
        const endPos = model.getPositionAt(match.index + match[0].length);
        markers.push({
          severity: 8, // MarkerSeverity.Error
          message: fp.description,
          source: "Brand",
          startLineNumber: startPos.lineNumber, startColumn: startPos.column,
          endLineNumber: endPos.lineNumber, endColumn: endPos.column,
        });
      }
    } catch {
      // Invalid regex pattern -- skip silently
    }
  }

  return markers;
}
