import type * as Monaco from "monaco-editor";
import { cssPropertyRules } from "./caniemail-data";

const OWNER = "caniemail";

export function runCssDiagnostics(
  monaco: typeof Monaco,
  model: Monaco.editor.ITextModel
): void {
  const markers: Monaco.editor.IMarkerData[] = [];
  const content = model.getValue();

  for (const rule of cssPropertyRules) {
    const pattern = rule.value
      ? new RegExp(
          `${escapeRegex(rule.property)}\\s*:\\s*${escapeRegex(rule.value)}`,
          "gi"
        )
      : new RegExp(`${escapeRegex(rule.property)}\\s*:`, "gi");

    let match: RegExpExecArray | null;
    while ((match = pattern.exec(content)) !== null) {
      const pos = model.getPositionAt(match.index);
      const endPos = model.getPositionAt(match.index + match[0].length);

      markers.push({
        severity:
          rule.severity === "error"
            ? monaco.MarkerSeverity.Error
            : monaco.MarkerSeverity.Warning,
        message: `${rule.reason}\nUnsupported in: ${rule.unsupportedClients.join(", ")}`,
        startLineNumber: pos.lineNumber,
        startColumn: pos.column,
        endLineNumber: endPos.lineNumber,
        endColumn: endPos.column,
        source: "Can I Email",
      });
    }
  }

  monaco.editor.setModelMarkers(model, OWNER, markers);
}

export function getDiagnosticCount(
  monaco: typeof Monaco,
  model: Monaco.editor.ITextModel
): number {
  return monaco.editor.getModelMarkers({ owner: OWNER, resource: model.uri })
    .length;
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
