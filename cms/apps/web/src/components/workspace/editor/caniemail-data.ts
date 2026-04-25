export interface CssPropertySupport {
  property: string;
  value: string | null;
  severity: "error" | "warning";
  unsupportedClients: string[];
  reason: string;
}

export const cssPropertyRules: CssPropertySupport[] = [
  // Errors — zero/near-zero email client support
  {
    property: "position",
    value: "fixed",
    severity: "error",
    unsupportedClients: ["Gmail", "Outlook", "Yahoo", "Apple Mail"],
    reason: "position:fixed is not supported in any major email client",
  },
  {
    property: "position",
    value: "sticky",
    severity: "error",
    unsupportedClients: ["Gmail", "Outlook", "Yahoo", "Apple Mail"],
    reason: "position:sticky is not supported in any major email client",
  },
  {
    property: "display",
    value: "grid",
    severity: "error",
    unsupportedClients: ["Outlook", "Gmail (Android)", "Yahoo"],
    reason: "display:grid has no support in Outlook and limited support elsewhere",
  },

  // Warnings — partial support
  {
    property: "display",
    value: "flex",
    severity: "warning",
    unsupportedClients: ["Outlook (Windows)", "Gmail (Android)"],
    reason: "display:flex is not supported in Outlook on Windows. Use tables for reliable layouts",
  },
  {
    property: "float",
    value: null,
    severity: "warning",
    unsupportedClients: ["Outlook (Windows)"],
    reason: "float is unreliable in Outlook. Use align attributes or tables",
  },
  {
    property: "max-width",
    value: null,
    severity: "warning",
    unsupportedClients: ["Outlook (Windows)"],
    reason: "max-width is ignored in Outlook on Windows. Use a fixed width with MSO conditionals",
  },
  {
    property: "background-image",
    value: null,
    severity: "warning",
    unsupportedClients: ["Outlook (Windows)"],
    reason: "background-image requires VML fallback for Outlook. Use <!--[if mso]> with v:fill",
  },
  {
    property: "border-radius",
    value: null,
    severity: "warning",
    unsupportedClients: ["Outlook (Windows)"],
    reason: "border-radius is ignored in Outlook on Windows. Rounded corners will appear square",
  },
  {
    property: "box-shadow",
    value: null,
    severity: "warning",
    unsupportedClients: ["Outlook (Windows)", "Gmail"],
    reason: "box-shadow is stripped by Gmail and ignored by Outlook on Windows",
  },
  {
    property: "opacity",
    value: null,
    severity: "warning",
    unsupportedClients: ["Outlook (Windows)"],
    reason: "opacity is not supported in Outlook on Windows",
  },
];
