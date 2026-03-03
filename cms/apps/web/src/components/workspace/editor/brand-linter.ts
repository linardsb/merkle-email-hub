import { linter, type Diagnostic } from "@codemirror/lint";
import type { Extension } from "@codemirror/state";
import type { BrandConfig } from "@/types/brand";

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function computeBrandDiagnostics(content: string, config: BrandConfig): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];
  const approvedHexes = new Set(config.colors.map((c) => c.hex.toLowerCase()));
  const approvedFonts = new Set(
    config.typography.map((t) => t.family.toLowerCase())
  );

  // Check for off-brand hex colors in CSS
  const colorPattern = /(?:color|background(?:-color)?)\s*:\s*(#[0-9a-fA-F]{3,8})/gi;
  let match: RegExpExecArray | null;
  while ((match = colorPattern.exec(content)) !== null) {
    const hex = match[1]!.toLowerCase();
    // Normalize 3-char hex to 6-char
    const normalized =
      hex.length === 4
        ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
        : hex;
    if (!approvedHexes.has(normalized)) {
      diagnostics.push({
        from: match.index,
        to: match.index + match[0].length,
        severity: "warning",
        message: `Off-brand color ${hex}. Approved colors: ${config.colors.map((c) => `${c.name} (${c.hex})`).join(", ")}`,
        source: "Brand",
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
      diagnostics.push({
        from: match.index,
        to: match.index + match[0].length,
        severity: "warning",
        message: `Off-brand font "${match[1]!.trim()}". Approved fonts: ${config.typography.map((t) => t.family).join(", ")}`,
        source: "Brand",
      });
    }
  }

  // Check forbidden patterns
  for (const fp of config.forbiddenPatterns) {
    try {
      const regex = new RegExp(fp.pattern, "gi");
      while ((match = regex.exec(content)) !== null) {
        diagnostics.push({
          from: match.index,
          to: match.index + match[0].length,
          severity: "error",
          message: fp.description,
          source: "Brand",
        });
      }
    } catch {
      // Invalid regex pattern — skip silently
    }
  }

  return diagnostics;
}

export function brandLinter(
  config: BrandConfig,
  onDiagnosticsChange?: (count: number) => void,
): Extension {
  return linter(
    (view) => {
      const content = view.state.doc.toString();
      const diagnostics = computeBrandDiagnostics(content, config);
      onDiagnosticsChange?.(diagnostics.length);
      return diagnostics;
    },
    { delay: 500 },
  );
}
