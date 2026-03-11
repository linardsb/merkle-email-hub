"use client";

import { useTranslations } from "next-intl";
import {
  Network,
  ArrowRight,
  Database,
  Code,
  Wrench,
  Monitor,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import type { GraphSearchResult, GraphEntity, GraphRelationship } from "@/types/graph-search";

/* ── Entity type → icon + colour mapping ── */
const ENTITY_STYLES: Record<string, { icon: typeof Network; colorClass: string }> = {
  email_client: { icon: Monitor, colorClass: "text-status-info" },
  css_property: { icon: Code, colorClass: "text-interactive" },
  technique: { icon: Wrench, colorClass: "text-status-warning" },
};

const DEFAULT_STYLE = { icon: Database, colorClass: "text-foreground-muted" };

/* ── Relationship type → label + icon ── */
const RELATIONSHIP_DISPLAY: Record<string, { icon: typeof ArrowRight; colorClass: string }> = {
  supports: { icon: CheckCircle2, colorClass: "text-status-success" },
  partially_supports: { icon: AlertTriangle, colorClass: "text-status-warning" },
  does_not_support: { icon: XCircle, colorClass: "text-status-error" },
  fallback_for: { icon: Wrench, colorClass: "text-status-info" },
  targets: { icon: ArrowRight, colorClass: "text-foreground-muted" },
};

const DEFAULT_REL = { icon: ArrowRight, colorClass: "text-foreground-muted" };

/* ── Sub-components ── */

function EntityCard({ entity }: { entity: GraphEntity }) {
  const style = ENTITY_STYLES[entity.entity_type] ?? DEFAULT_STYLE;
  const Icon = style.icon;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-3">
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${style.colorClass}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-foreground">{entity.name}</span>
          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            {entity.entity_type.replace(/_/g, " ")}
          </span>
        </div>
        {entity.description && (
          <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
            {entity.description}
          </p>
        )}
        {Object.keys(entity.properties).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.entries(entity.properties).map(([key, value]) => (
              <span
                key={key}
                className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
              >
                {key}: {String(value)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RelationshipRow({
  relationship,
  entityMap,
}: {
  relationship: GraphRelationship;
  entityMap: Map<string, GraphEntity>;
}) {
  const t = useTranslations("knowledge");
  const display = RELATIONSHIP_DISPLAY[relationship.relationship_type] ?? DEFAULT_REL;
  const RelIcon = display.icon;
  const source = entityMap.get(relationship.source_id);
  const target = entityMap.get(relationship.target_id);

  // Use i18n key for relationship type, with fallback
  const relKey = `rel_${relationship.relationship_type}`;
  const relLabel = t.has(relKey as Parameters<typeof t>[0])
    ? t(relKey as Parameters<typeof t>[0])
    : relationship.relationship_type.replace(/_/g, " ");

  return (
    <div className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-2 text-sm">
      <span className="font-medium text-foreground">
        {source?.name ?? relationship.source_id}
      </span>
      <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />
      <span className="flex items-center gap-1">
        <RelIcon className={`h-3.5 w-3.5 ${display.colorClass}`} />
        <span className={display.colorClass}>{relLabel}</span>
      </span>
      <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />
      <span className="font-medium text-foreground">
        {target?.name ?? relationship.target_id}
      </span>
    </div>
  );
}

/* ── Main Component ── */

interface GraphSearchResultsProps {
  results: GraphSearchResult[];
}

export function GraphSearchResults({ results }: GraphSearchResultsProps) {
  const t = useTranslations("knowledge");

  if (results.length === 0) return null;

  // Build entity map for relationship lookups
  const entityMap = new Map<string, GraphEntity>();
  for (const result of results) {
    for (const entity of result.entities) {
      entityMap.set(entity.id, entity);
    }
  }

  return (
    <div className="animate-fade-in space-y-6">
      {results.map((result, i) => {
        // Group entities by type
        const grouped = new Map<string, GraphEntity[]>();
        for (const entity of result.entities) {
          const group = grouped.get(entity.entity_type) ?? [];
          group.push(entity);
          grouped.set(entity.entity_type, group);
        }

        return (
          <div key={i} className="space-y-4">
            {/* Summary */}
            <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-4">
              <Network className="mt-0.5 h-5 w-5 shrink-0 text-interactive" />
              <div>
                <p className="text-sm text-foreground">{result.content}</p>
                {result.score > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t("graphRelevance", { score: Math.round(result.score * 100) })}
                  </p>
                )}
              </div>
            </div>

            {/* Entities grouped by type */}
            {Array.from(grouped.entries()).map(([type, entities]) => {
              const typeKey = `entityType_${type}`;
              const typeLabel = t.has(typeKey as Parameters<typeof t>[0])
                ? t(typeKey as Parameters<typeof t>[0])
                : type.replace(/_/g, " ");

              return (
                <div key={type}>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {typeLabel}
                    <span className="ml-1.5 opacity-70">({entities.length})</span>
                  </h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {entities.map((entity) => (
                      <EntityCard key={entity.id} entity={entity} />
                    ))}
                  </div>
                </div>
              );
            })}

            {/* Relationships */}
            {result.relationships.length > 0 && (
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {t("graphRelationships")}
                  <span className="ml-1.5 opacity-70">({result.relationships.length})</span>
                </h3>
                <div className="space-y-1.5">
                  {result.relationships.map((rel, ri) => (
                    <RelationshipRow key={ri} relationship={rel} entityMap={entityMap} />
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
