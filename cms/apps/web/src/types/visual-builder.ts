import type { ComponentResponse } from "@email-hub/sdk";

/** Category constants for the component palette (must match backend seed categories) */
export const SECTION_CATEGORIES = [
  "structure",
  "content",
  "action",
  "social",
  "commerce",
] as const;
export type SectionCategory = (typeof SECTION_CATEGORIES)[number];

/** Slot types supported by the component system */
export type SlotType =
  | "headline"
  | "subheadline"
  | "body"
  | "cta"
  | "image"
  | "preheader"
  | "footer"
  | "nav"
  | "social"
  | "divider";

/** Slot definition from ComponentVersion.slot_definitions */
export interface SlotDefinition {
  slot_id: string;
  slot_type: SlotType;
  selector: string;
  required: boolean;
  max_chars: number | null;
  placeholder: string;
  label: string;
}

/** Design token defaults from ComponentVersion.default_tokens */
export interface DefaultTokens {
  colors: Record<string, string>;
  fonts: Record<string, string>;
  font_sizes: Record<string, string>;
  spacing: Record<string, string>;
}

/** Responsive overrides stored per-section */
export interface ResponsiveOverrides {
  stackOnMobile: boolean;
  fullWidthImageOnMobile: boolean;
  mobileFontSize: string | null;
  mobileHide: boolean;
  mobilePaddingOverride: string | null;
  mobileTextAlign: string | null;
}

/** Advanced section config */
export interface AdvancedConfig {
  customCssClass: string;
  msoConditional: boolean;
  darkModeOverrides: Record<string, string>;
  htmlAttributes: Record<string, string>;
}

/** A section placed on the canvas */
export interface BuilderSection {
  /** Unique instance ID (crypto.randomUUID) */
  id: string;
  /** Source component from the library */
  componentId: number;
  componentName: string;
  componentSlug: string;
  category: SectionCategory | string;
  /** Rendered HTML for this section (from component version html_source with slot fills applied) */
  html: string;
  /** CSS source from the component version */
  css: string | null;
  /** Slot values filled by the user (slot name → content string) */
  slotFills: Record<string, string>;
  /** Design token overrides (token name → value) */
  tokenOverrides: Record<string, unknown>;
  /** Slot definitions from the component version */
  slotDefinitions: SlotDefinition[];
  /** Default token values from the component version */
  defaultTokens: DefaultTokens | null;
  /** Responsive behavior overrides */
  responsive: ResponsiveOverrides;
  /** Advanced configuration */
  advanced: AdvancedConfig;
}

/** Default responsive overrides for new sections */
export const DEFAULT_RESPONSIVE: ResponsiveOverrides = {
  stackOnMobile: false,
  fullWidthImageOnMobile: false,
  mobileFontSize: null,
  mobileHide: false,
  mobilePaddingOverride: null,
  mobileTextAlign: null,
};

/** Default advanced config for new sections */
export const DEFAULT_ADVANCED: AdvancedConfig = {
  customCssClass: "",
  msoConditional: false,
  darkModeOverrides: {},
  htmlAttributes: {},
};

/** Undo/redo history entry */
export interface HistoryEntry {
  sections: BuilderSection[];
  timestamp: number;
}

/** Builder state managed by useBuilderState */
export interface BuilderState {
  sections: BuilderSection[];
  selectedSectionId: string | null;
  history: HistoryEntry[];
  historyIndex: number;
}

/** Palette item: a component available for dragging onto the canvas */
export interface PaletteItem {
  component: ComponentResponse;
  /** Pre-fetched latest version HTML for thumbnail preview */
  previewHtml: string | null;
}

export type BuilderAction =
  | { type: "ADD_SECTION"; section: BuilderSection; atIndex?: number }
  | { type: "REMOVE_SECTION"; sectionId: string }
  | { type: "DUPLICATE_SECTION"; sectionId: string }
  | { type: "MOVE_SECTION"; fromIndex: number; toIndex: number }
  | { type: "UPDATE_SECTION"; sectionId: string; updates: Partial<BuilderSection> }
  | { type: "SELECT_SECTION"; sectionId: string | null }
  | { type: "SET_SECTIONS"; sections: BuilderSection[] }
  | { type: "UNDO" }
  | { type: "REDO" };

/** Parsed section from HTML — used for code ↔ builder roundtrip */
export interface SectionNode {
  /** Matches BuilderSection.id when from builder, or generated from data-section-id attr */
  id: string;
  /** Component ID from data-component-id attr, or 0 for unrecognized sections */
  componentId: number;
  /** Component name from section comment or data attr */
  componentName: string;
  /** Slot values extracted from data-slot-name elements */
  slotValues: Record<string, string>;
  /** Inline style overrides found on the section wrapper */
  styleOverrides: Record<string, string>;
  /** The raw HTML fragment for this section (between section boundaries) */
  htmlFragment: string;
  /** Non-section content (comments, text) preceding this section */
  precedingContent?: string;
}

/** Diff operation for incremental section updates */
export interface SectionDiff {
  type: "add" | "remove" | "update" | "move";
  sectionId: string;
  index?: number;
  updates?: Partial<SectionNode>;
}

/** Sync status between code editor and visual builder */
export type SyncStatus = "synced" | "syncing" | "parse_error" | "conflict";
