import { linter, type Diagnostic } from "@codemirror/lint";
import type { Extension } from "@codemirror/state";
import { cssPropertyRules } from "./caniemail-data";

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function computeDiagnostics(content: string): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];

  for (const rule of cssPropertyRules) {
    const pattern = rule.value
      ? new RegExp(
          `${escapeRegex(rule.property)}\\s*:\\s*${escapeRegex(rule.value)}`,
          "gi"
        )
      : new RegExp(`${escapeRegex(rule.property)}\\s*:`, "gi");

    let match: RegExpExecArray | null;
    while ((match = pattern.exec(content)) !== null) {
      diagnostics.push({
        from: match.index,
        to: match.index + match[0].length,
        severity: rule.severity === "error" ? "error" : "warning",
        message: `${rule.reason}\nUnsupported in: ${rule.unsupportedClients.join(", ")}`,
        source: "Can I Email",
      });
    }
  }

  return diagnostics;
}

export function canIEmailLinter(
  onDiagnosticsChange?: (count: number) => void
): Extension {
  return linter(
    (view) => {
      const content = view.state.doc.toString();
      const diagnostics = computeDiagnostics(content);
      onDiagnosticsChange?.(diagnostics.length);
      return diagnostics;
    },
    { delay: 300 }
  );
}
