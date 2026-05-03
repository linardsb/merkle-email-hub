#!/usr/bin/env node
/**
 * Generate React icon components from SVG source files.
 * Processes SVGs: removes hardcoded colors, uses currentColor, outputs TSX.
 *
 * Emits one file per icon under `src/components/icons/generated/` plus a
 * regenerated barrel at `src/components/icons/index.ts`.
 *
 * Usage:
 *   node scripts/generate-icons.mjs
 *   pnpm exec prettier --write src/components/icons   # always re-format after regenerating
 */
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ICONS_ROOT = resolve(__dirname, "../../../../email-templates/Icons");
const OUTPUT_DIR = resolve(__dirname, "../src/components/icons");

// ── Icon Mapping ─────────────────────────────────────────────────────
// key = React export name (matches lucide-react naming)
// value = { source: 'brand'|'small'|'stroke', path: relative to ICONS_ROOT }
const ICON_MAP = {
  Activity: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Metrics-black.svg",
  },
  BarChart3: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Data-Report-black.svg",
  },
  Blocks: { source: "small", path: "Small Icons/Electronics and Devices/circuitry-fill.svg" },
  BookOpen: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Knowledge-black.svg",
  },
  Bot: { source: "brand", path: "Merkle Brand/Artificial Intelligence/32x32-AI-person-black.svg" },
  Brain: { source: "brand", path: "Merkle Brand/Artificial Intelligence/32x32-AI-brain-black.svg" },
  Building2: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Bank-black.svg" },
  Calendar: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Alarm-black.svg",
  },
  Camera: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-Camera-black.svg" },
  ChartLine: { source: "small", path: "Small Icons/Data Analysis /chart-line-fill.svg" },
  ChartLineUp: { source: "small", path: "Small Icons/Data Analysis /chart-line-up-fill.svg" },
  ClipboardCheck: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-checklist-black.svg",
  },
  ClipboardList: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-checklist-black.svg",
  },
  Clock: { source: "small", path: "Small Icons/Travel/compass-fill.svg" },
  Cloud: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Cloud-black.svg",
  },
  CloudUpload: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Cloud-black.svg",
  },
  Code: { source: "brand", path: "Merkle Brand/Artificial Intelligence/32x32-AI-chip-black.svg" },
  Code2: { source: "brand", path: "Merkle Brand/Artificial Intelligence/32x32-AI-chip-black.svg" },
  Cog: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Settings-black.svg",
  },
  Database: { source: "small", path: "Small Icons/Electronics and Devices/database-fill.svg" },
  Devices: { source: "small", path: "Small Icons/Electronics and Devices/devices-fill.svg" },
  Download: { source: "small", path: "Small Icons/Travel/rocket-launch-fill.svg" },
  Eye: { source: "small", path: "Small Icons/Travel/compass-fill.svg" },
  FileCode: { source: "small", path: "Small Icons/Electronics and Devices/code-block-fill.svg" },
  FileSpreadsheet: { source: "small", path: "Small Icons/Data Analysis /file-csv-fill.svg" },
  FileText: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Document-black.svg" },
  FlaskConical: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_beaker-science_06.svg",
  },
  FolderOpen: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-briefcase-black.svg" },
  GitBranch: { source: "small", path: "Small Icons/Data Analysis /tree-structure-fill.svg" },
  Globe: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Global-black.svg" },
  History: { source: "small", path: "Small Icons/Travel/signpost-fill.svg" },
  Inbox: { source: "small", path: "Small Icons/Travel/mailbox-fill.svg" },
  Key: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg" },
  KeyRound: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  Layers: { source: "small", path: "Small Icons/Travel/books-fill.svg" },
  LayoutDashboard: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Pie-Chart-black.svg",
  },
  Lightbulb: {
    source: "brand",
    path: "Merkle Brand/Artificial Intelligence/32x32-AI-idea-black.svg",
  },
  ListChecks: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-checklist-black.svg",
  },
  Mail: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Email-black.svg",
  },
  MessageSquare: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Online-Chat-black.svg",
  },
  Mic: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-microphone-black.svg" },
  Monitor: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-desktop-black.svg",
  },
  MonitorSmartphone: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Mobile-Tablet-black.svg",
  },
  Network: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Networking-black.svg",
  },
  Package: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Package-black.svg",
  },
  Paintbrush: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Creative-black.svg",
  },
  Palette: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Creative-black.svg",
  },
  PenTool: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Creative-black.svg",
  },
  Play: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Submit-Click-black.svg",
  },
  Plug: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Enviroment-Electric-Plug-black.svg",
  },
  Printer: { source: "small", path: "Small Icons/Data Analysis /presentation-chart-fill.svg" },
  Puzzle: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Problem-Solving-black.svg",
  },
  Search: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-search-black.svg",
  },
  Send: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Launch-black.svg",
  },
  Server: { source: "small", path: "Small Icons/Data Analysis /hard-drives-fill.svg" },
  Shield: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  ShieldAlert: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  ShieldCheck: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  ShieldX: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  Smartphone: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-mobile-black.svg",
  },
  Sparkles: {
    source: "brand",
    path: "Merkle Brand/Artificial Intelligence/32x32-AI-idea-black.svg",
  },
  Sun: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Sun-black.svg" },
  Tablet: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Mobile-Tablet-black.svg",
  },
  Target: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Target-black.svg" },
  Trophy: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Trophy-black.svg" },
  Upload: { source: "small", path: "Small Icons/Travel/rocket-fill.svg" },
  User: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Individual-Avatar-black.svg",
  },
  UserCheck: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Checkmark-black.svg",
  },
  UserRoundPen: { source: "small", path: "Small Icons/People/user-gear-fill.svg" },
  Users: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Large-Team-black.svg",
  },
  Wand2: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Creative-black.svg",
  },
  Workflow: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Settings-black.svg",
  },
  Zap: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Electric-black.svg" },
};

// ── SVG Processing ───────────────────────────────────────────────────

function processBrandSvg(content) {
  // Remove XML declaration
  content = content.replace(/<\?xml[^?]*\?>\s*/g, "");

  // Extract style classes → fill values
  const styleMap = {};
  const styleMatch = content.match(/<style[^>]*>([\s\S]*?)<\/style>/);
  if (styleMatch) {
    for (const rule of styleMatch[1].matchAll(/\.([\w-]+)\s*\{([^}]*)\}/g)) {
      const className = rule[1];
      const fillMatch = rule[2].match(/fill:\s*([^;]+)/);
      if (fillMatch) {
        styleMap[className] = fillMatch[1].trim();
      }
    }
  }

  // Remove <defs>...</defs> and <style>...</style> (may appear outside defs).
  // Loop until stable: nested/overlapping tags can survive a single pass.
  let prevContent;
  do {
    prevContent = content;
    content = content.replace(/<defs>[\s\S]*?<\/defs>\s*/g, "");
    content = content.replace(/<style[^>]*>[\s\S]*?<\/style>\s*/g, "");
  } while (content !== prevContent);

  // Replace class references
  content = content.replace(/\s*class="([\w-]+)"/g, (_match, className) => {
    const fill = styleMap[className];
    if (fill === "none") return ' fill="none"';
    return ""; // will inherit currentColor
  });

  // Extract viewBox
  const viewBoxMatch = content.match(/viewBox="([^"]+)"/);
  const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 32 32";

  // Extract inner content
  const innerMatch = content.match(/<svg[^>]*>([\s\S]*)<\/svg>/);
  let inner = innerMatch ? innerMatch[1].trim() : "";

  // Clean attributes
  inner = inner
    .replace(/\s*id="[^"]*"/g, "")
    .replace(/\s*data-name="[^"]*"/g, "")
    .replace(/\s*xmlns:xlink="[^"]*"/g, "");

  // Remove empty groups (repeat to handle nesting)
  for (let i = 0; i < 3; i++) {
    inner = inner.replace(/<g\s*>([\s\S]*?)<\/g>/g, "$1");
  }

  return { viewBox, inner };
}

function processSmallSvg(content) {
  // These are simple: single fill color on <svg>, paths inside
  const viewBoxMatch = content.match(/viewBox="([^"]+)"/);
  const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 256 256";

  const innerMatch = content.match(/<svg[^>]*>([\s\S]*)<\/svg>/);
  let inner = innerMatch ? innerMatch[1].trim() : "";

  // Remove <defs>...</defs> and <style>...</style> blocks.
  // Loop until stable: nested/overlapping tags can survive a single pass.
  let prevInner;
  do {
    prevInner = inner;
    inner = inner.replace(/<defs>[\s\S]*?<\/defs>\s*/g, "");
    inner = inner.replace(/<style[^>]*>[\s\S]*?<\/style>\s*/g, "");
  } while (inner !== prevInner);

  // Remove class attributes (styles already removed)
  inner = inner.replace(/\s*class="[^"]*"/g, "");

  // Remove any fill attributes from inner paths (they'll inherit currentColor)
  inner = inner.replace(/\s*fill="[^"]*"/g, "");

  return { viewBox, inner };
}

function processStrokeSvg(content) {
  const viewBoxMatch = content.match(/viewBox="([^"]+)"/);
  const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 72 65";

  const innerMatch = content.match(/<svg[^>]*>([\s\S]*)<\/svg>/);
  let inner = innerMatch ? innerMatch[1].trim() : "";

  // Replace hardcoded stroke color with currentColor
  inner = inner.replace(/stroke="#[0-9a-fA-F]+"/g, 'stroke="currentColor"');

  // Replace hardcoded fill colors with currentColor (but not fill="none")
  inner = inner.replace(/fill="#[0-9a-fA-F]+"/g, 'fill="currentColor"');

  // Clean IDs and data attributes
  inner = inner.replace(/\s*id="[^"]*"/g, "").replace(/\s*data-name="[^"]*"/g, "");

  // Remove ALL <g> tags (opening with any attrs, and closing) — flatten structure
  inner = inner.replace(/<g[^>]*>/g, "").replace(/<\/g>/g, "");

  return { viewBox, inner, isStroke: true };
}

// ── JSX conversion ───────────────────────────────────────────────────

function svgInnerToJsx(inner) {
  // Remove HTML/XML comments (invalid in JSX).
  // Loop until stable: nested/overlapping comment markers can survive a single pass.
  let prevInner;
  do {
    prevInner = inner;
    inner = inner.replace(/<!--[\s\S]*?-->/g, "");
  } while (inner !== prevInner);

  // Convert SVG attributes to JSX camelCase
  return (
    inner
      .replace(/stroke-width/g, "strokeWidth")
      .replace(/stroke-linejoin/g, "strokeLinejoin")
      .replace(/stroke-linecap/g, "strokeLinecap")
      .replace(/stroke-miterlimit/g, "strokeMiterlimit")
      .replace(/fill-rule/g, "fillRule")
      .replace(/clip-rule/g, "clipRule")
      .replace(/clip-path/g, "clipPath")
      .replace(/xmlns:xlink/g, "xmlnsXlink")
      .replace(/xlink:href/g, "xlinkHref")
      // Self-close tags that aren't self-closed
      .replace(/<(\w+)([^>]*?)><\/\1>/g, "<$1$2 />")
      // Ensure self-closing tags end properly
      .replace(/<(path|line|rect|circle|ellipse|polygon|polyline)([^/]*?)(?<!\/)>/g, "<$1$2 />")
  );
}

// ── Lucide-react fallback set ────────────────────────────────────────
// Icons re-exported from `lucide-react` because no custom equivalent exists.
// Keep alphabetised. Adding/removing entries requires regenerating the barrel.
const LUCIDE_FALLBACK = [
  "AlertCircle",
  "AlertTriangle",
  "AlignCenter",
  "AlignLeft",
  "AlignRight",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "ArrowRightLeft",
  "Ban",
  "Braces",
  "Bug",
  "Check",
  "CheckCircle",
  "CheckCircle2",
  "ChevronDown",
  "ChevronLeft",
  "ChevronRight",
  "ChevronUp",
  "Columns",
  "Component",
  "Copy",
  "ExternalLink",
  "EyeOff",
  "Figma",
  "FileSearch",
  "Filter",
  "Frame",
  "GitCommitVertical",
  "GitCompareArrows",
  "GripHorizontal",
  "GripVertical",
  "Group",
  "Image",
  "ImageOff",
  "ImagePlus",
  "Info",
  "Languages",
  "Layout",
  "Link",
  "Link2",
  "Loader2",
  "LogOut",
  "Maximize2",
  "Moon",
  "MoreVertical",
  "MousePointer",
  "MousePointerClick",
  "PanelBottom",
  "PanelRight",
  "Paperclip",
  "Pause",
  "Pencil",
  "Plus",
  "RefreshCw",
  "Repeat",
  "RotateCcw",
  "Save",
  "SkipForward",
  "Square",
  "Tag",
  "ToggleLeft",
  "ToggleRight",
  "Trash2",
  "Type",
  "Variable",
  "WifiOff",
  "WrapText",
  "Wrench",
  "X",
  "XCircle",
  "ZoomIn",
  "ZoomOut",
];

// ── Code Generation ──────────────────────────────────────────────────

function generateIconFile(name, viewBox, jsxInner, isStroke = false) {
  const fillAttr = isStroke ? 'fill="none" stroke="currentColor"' : 'fill="currentColor"';
  return `/**
 * ${name} icon — auto-generated from SVG source.
 * Do not edit manually — regenerate with: node scripts/generate-icons.mjs
 */
import { forwardRef } from "react";
import type { IconProps } from "./_types";

export const ${name} = forwardRef<SVGSVGElement, IconProps>(
  ({ size = 24, className, ...props }, ref) => (
    <svg
      ref={ref}
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="${viewBox}"
      ${fillAttr}
      className={className}
      {...props}
    >
      ${jsxInner}
    </svg>
  ),
);
${name}.displayName = "${name}";
`;
}

const TYPES_FILE = `/**
 * Shared icon prop type — auto-generated.
 * Do not edit manually — regenerate with: node scripts/generate-icons.mjs
 */
import type { SVGProps } from "react";

export interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number | string;
}
`;

function generateBarrel(iconNames) {
  const customExports = iconNames
    .map((name) => `export { ${name} } from "./generated/${name}";`)
    .join("\n");
  const lucideExports = LUCIDE_FALLBACK.map((name) => `  ${name},`).join("\n");
  return `/**
 * Unified icon barrel — auto-generated. Do not edit manually.
 * Regenerate with: node scripts/generate-icons.mjs
 *
 * Custom icons (per-file under ./generated) replace lucide-react where available;
 * lucide-react provides the rest.
 */

// ── Custom icon replacements (${iconNames.length} icons — auto-generated) ──
${customExports}

export type { IconProps } from "./generated/_types";

// ── Lucide-react fallbacks (${LUCIDE_FALLBACK.length} icons — no custom equivalent) ──
export {
${lucideExports}
} from "lucide-react";

// Re-export the LucideIcon type for components that use it for prop typing
export type { LucideIcon } from "lucide-react";
`;
}

// ── Main ─────────────────────────────────────────────────────────────

const GENERATED_DIR = resolve(OUTPUT_DIR, "generated");
mkdirSync(GENERATED_DIR, { recursive: true });

// Write shared types file
writeFileSync(resolve(GENERATED_DIR, "_types.ts"), TYPES_FILE);

// Track unique SVGs (some icons share the same source)
const processedSvgs = new Map(); // path → { viewBox, jsxInner, isStroke }

const generatedNames = [];
const errors = [];

for (const [name, config] of Object.entries(ICON_MAP)) {
  const fullPath = resolve(ICONS_ROOT, config.path);

  let processed;
  if (processedSvgs.has(config.path)) {
    processed = processedSvgs.get(config.path);
  } else {
    try {
      const content = readFileSync(fullPath, "utf-8");
      switch (config.source) {
        case "brand":
          processed = processBrandSvg(content);
          break;
        case "small":
          processed = processSmallSvg(content);
          break;
        case "stroke":
          processed = processStrokeSvg(content);
          break;
        default:
          throw new Error(`Unknown source type: ${config.source}`);
      }
      processed.jsxInner = svgInnerToJsx(processed.inner);
      processedSvgs.set(config.path, processed);
    } catch (err) {
      errors.push(`${name}: ${err.message}`);
      continue;
    }
  }

  const fileContent = generateIconFile(
    name,
    processed.viewBox,
    processed.jsxInner,
    processed.isStroke,
  );
  writeFileSync(resolve(GENERATED_DIR, `${name}.tsx`), fileContent);
  generatedNames.push(name);
}

// Regenerate the unified barrel
writeFileSync(resolve(OUTPUT_DIR, "index.ts"), generateBarrel(generatedNames));

console.log(`Generated ${generatedNames.length} icon files in ${GENERATED_DIR}`);
console.log(`Regenerated barrel at ${resolve(OUTPUT_DIR, "index.ts")}`);
if (errors.length > 0) {
  console.error("Errors:", errors);
  process.exit(1);
}
