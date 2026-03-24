import type { editor } from "monaco-editor";
import { cssPropertyRules } from "./caniemail-data";

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function computeCssMarkers(model: editor.ITextModel): editor.IMarkerData[] {
  const content = model.getValue();
  const markers: editor.IMarkerData[] = [];

  for (const rule of cssPropertyRules) {
    const pattern = rule.value
      ? new RegExp(`${escapeRegex(rule.property)}\\s*:\\s*${escapeRegex(rule.value)}`, "gi")
      : new RegExp(`${escapeRegex(rule.property)}\\s*:`, "gi");

    let match: RegExpExecArray | null;
    while ((match = pattern.exec(content)) !== null) {
      const startPos = model.getPositionAt(match.index);
      const endPos = model.getPositionAt(match.index + match[0].length);
      markers.push({
        severity: rule.severity === "error" ? 8 : 4, // MarkerSeverity.Error : Warning
        message: `${rule.reason}\nUnsupported in: ${rule.unsupportedClients.join(", ")}`,
        source: "Can I Email",
        startLineNumber: startPos.lineNumber, startColumn: startPos.column,
        endLineNumber: endPos.lineNumber, endColumn: endPos.column,
      });
    }
  }
  return markers;
}
