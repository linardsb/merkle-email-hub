import type { GraphEntity, GraphRelationship, GraphSearchResult } from "@/types/graph-search";

// Entities representing email clients
const ENTITY_OUTLOOK_WINDOWS: GraphEntity = {
  id: "ec-outlook-windows",
  name: "Outlook (Windows)",
  entity_type: "email_client",
  description: "Microsoft Outlook desktop client for Windows using Word rendering engine",
  properties: { rendering_engine: "Word", market_share: "27%", platform: "desktop" },
};

const ENTITY_GMAIL: GraphEntity = {
  id: "ec-gmail",
  name: "Gmail",
  entity_type: "email_client",
  description: "Google Gmail web client with strict CSS sanitisation",
  properties: { rendering_engine: "Blink", market_share: "30%", platform: "web" },
};

const ENTITY_APPLE_MAIL: GraphEntity = {
  id: "ec-apple-mail",
  name: "Apple Mail (iOS)",
  entity_type: "email_client",
  description: "Apple Mail on iOS with full WebKit rendering support",
  properties: { rendering_engine: "WebKit", market_share: "35%", platform: "mobile" },
};

// CSS property entities
const ENTITY_FLEXBOX: GraphEntity = {
  id: "css-flexbox",
  name: "display: flex",
  entity_type: "css_property",
  description: "CSS Flexbox layout model for flexible box layouts",
  properties: { category: "layout", spec_status: "W3C Recommendation" },
};

const ENTITY_GRID: GraphEntity = {
  id: "css-grid",
  name: "display: grid",
  entity_type: "css_property",
  description: "CSS Grid Layout for two-dimensional layouts",
  properties: { category: "layout", spec_status: "W3C Recommendation" },
};

const ENTITY_DARK_MODE: GraphEntity = {
  id: "css-dark-mode",
  name: "prefers-color-scheme: dark",
  entity_type: "css_property",
  description: "Media query for dark mode preference detection",
  properties: { category: "media_queries", spec_status: "W3C Recommendation" },
};

const ENTITY_COLOR_SCHEME: GraphEntity = {
  id: "css-color-scheme",
  name: "color-scheme",
  entity_type: "css_property",
  description: "CSS property to indicate supported color schemes",
  properties: { category: "colors", spec_status: "W3C Recommendation" },
};

const ENTITY_MSO_CONDITIONAL: GraphEntity = {
  id: "tech-mso-conditional",
  name: "MSO Conditional Comments",
  entity_type: "technique",
  description: "Microsoft Office conditional comments for Outlook-specific targeting",
  properties: { category: "fallback", target: "Outlook (Windows)" },
};

const ENTITY_VML: GraphEntity = {
  id: "tech-vml",
  name: "VML Backgrounds",
  entity_type: "technique",
  description: "Vector Markup Language for Outlook background image support",
  properties: { category: "fallback", target: "Outlook (Windows)" },
};

const ENTITY_TABLE_LAYOUT: GraphEntity = {
  id: "css-table-layout",
  name: "Table-based Layout",
  entity_type: "technique",
  description: "Traditional table-based email layout for maximum compatibility",
  properties: { category: "layout", support_level: "universal" },
};

// Relationships
const ALL_RELATIONSHIPS: GraphRelationship[] = [
  // Outlook support
  { source_id: "ec-outlook-windows", target_id: "css-flexbox", relationship_type: "does_not_support", properties: { severity: "critical" } },
  { source_id: "ec-outlook-windows", target_id: "css-grid", relationship_type: "does_not_support", properties: { severity: "critical" } },
  { source_id: "ec-outlook-windows", target_id: "css-dark-mode", relationship_type: "partially_supports", properties: { notes: "Requires MSO conditional override" } },
  { source_id: "ec-outlook-windows", target_id: "css-color-scheme", relationship_type: "does_not_support", properties: { severity: "high" } },
  { source_id: "tech-mso-conditional", target_id: "ec-outlook-windows", relationship_type: "targets", properties: {} },
  { source_id: "tech-vml", target_id: "ec-outlook-windows", relationship_type: "targets", properties: {} },

  // Gmail support
  { source_id: "ec-gmail", target_id: "css-flexbox", relationship_type: "does_not_support", properties: { severity: "critical" } },
  { source_id: "ec-gmail", target_id: "css-grid", relationship_type: "does_not_support", properties: { severity: "critical" } },
  { source_id: "ec-gmail", target_id: "css-dark-mode", relationship_type: "supports", properties: {} },
  { source_id: "ec-gmail", target_id: "css-color-scheme", relationship_type: "supports", properties: {} },

  // Apple Mail support
  { source_id: "ec-apple-mail", target_id: "css-flexbox", relationship_type: "supports", properties: {} },
  { source_id: "ec-apple-mail", target_id: "css-grid", relationship_type: "supports", properties: {} },
  { source_id: "ec-apple-mail", target_id: "css-dark-mode", relationship_type: "supports", properties: {} },
  { source_id: "ec-apple-mail", target_id: "css-color-scheme", relationship_type: "supports", properties: {} },

  // Fallback techniques
  { source_id: "css-table-layout", target_id: "css-flexbox", relationship_type: "fallback_for", properties: {} },
  { source_id: "css-table-layout", target_id: "css-grid", relationship_type: "fallback_for", properties: {} },
  { source_id: "tech-mso-conditional", target_id: "css-dark-mode", relationship_type: "fallback_for", properties: { context: "Outlook only" } },
  { source_id: "tech-vml", target_id: "css-flexbox", relationship_type: "fallback_for", properties: { context: "Background images in Outlook" } },
];

const ALL_ENTITIES: GraphEntity[] = [
  ENTITY_OUTLOOK_WINDOWS, ENTITY_GMAIL, ENTITY_APPLE_MAIL,
  ENTITY_FLEXBOX, ENTITY_GRID, ENTITY_DARK_MODE, ENTITY_COLOR_SCHEME,
  ENTITY_MSO_CONDITIONAL, ENTITY_VML, ENTITY_TABLE_LAYOUT,
];

/** Build demo graph search results for a query */
export function buildDemoGraphSearchResults(
  query: string,
  topK: number = 10,
): GraphSearchResult[] {
  const q = query.toLowerCase();

  // Find matching entities (name, description, or type matches query)
  const matchedEntities = ALL_ENTITIES.filter((e) => {
    const text = `${e.name} ${e.description} ${e.entity_type}`.toLowerCase();
    return q.split(/\s+/).some((word) => text.includes(word));
  }).slice(0, topK);

  if (matchedEntities.length === 0) return [];

  // Gather entity IDs
  const entityIds = new Set(matchedEntities.map((e) => e.id));

  // Find relationships involving matched entities
  const matchedRelationships = ALL_RELATIONSHIPS.filter(
    (r) => entityIds.has(r.source_id) || entityIds.has(r.target_id),
  );

  // Include related entities not yet in the set
  const relatedEntityIds = new Set<string>();
  for (const r of matchedRelationships) {
    if (!entityIds.has(r.source_id)) relatedEntityIds.add(r.source_id);
    if (!entityIds.has(r.target_id)) relatedEntityIds.add(r.target_id);
  }
  const relatedEntities = ALL_ENTITIES.filter((e) => relatedEntityIds.has(e.id));
  const allResultEntities = [...matchedEntities, ...relatedEntities];

  // Build summary content
  const entityNames = matchedEntities.map((e) => e.name).join(", ");
  const content = `Found ${allResultEntities.length} entities related to "${query}": ${entityNames}. ` +
    `${matchedRelationships.length} relationships identified across email clients and CSS properties.`;

  return [
    {
      content,
      entities: allResultEntities,
      relationships: matchedRelationships,
      score: 0.92,
    },
  ];
}

/** Build demo completion response */
export function buildDemoGraphCompletion(query: string): string {
  const q = query.toLowerCase();

  if (q.includes("outlook") && q.includes("dark")) {
    return "Outlook on Windows has limited dark mode support. It does not natively support `prefers-color-scheme: dark` media queries or the `color-scheme` CSS property. To implement dark mode for Outlook, you need to use MSO conditional comments (`<!--[if mso]>`) to provide Outlook-specific overrides, and include `<meta name=\"color-scheme\" content=\"light dark\">` for clients that do support it. Apple Mail (iOS) and Gmail both fully support `prefers-color-scheme: dark`. The recommended approach is to use a progressive enhancement strategy: design for light mode first, add dark mode via media queries, and use MSO conditionals for Outlook fallbacks.";
  }

  if (q.includes("flexbox") || q.includes("grid")) {
    return "CSS Flexbox (`display: flex`) and CSS Grid (`display: grid`) are not supported in Outlook (Windows) or Gmail. These clients use rendering engines (Word for Outlook, Blink with sanitisation for Gmail) that strip modern layout properties. The universal fallback is table-based layout using `<table>`, `<tr>`, and `<td>` elements. Apple Mail (iOS) fully supports both Flexbox and Grid via its WebKit engine. For cross-client compatibility, always use table-based layouts as your primary structure and progressively enhance with Flexbox/Grid for clients that support them.";
  }

  return `Based on the knowledge graph, here's what I found about "${query}": The email development ontology tracks 25 email clients and 365 CSS properties with support relationships. Each property has per-client support levels (full, partial, none) with fallback techniques documented. Use the Graph search mode to explore specific entity relationships.`;
}
