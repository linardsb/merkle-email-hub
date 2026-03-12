/**
 * Demo mode URL resolver.
 * Maps GET API paths to mock data responses.
 * Returns null if the path doesn't match any known pattern.
 */

import { DEMO_ORGS } from "./data/orgs";
import { DEMO_PROJECTS } from "./data/projects";
import { DEMO_TEMPLATES, DEMO_VERSIONS } from "./data/templates";
import { DEMO_COMPONENTS, DEMO_COMPONENT_VERSIONS, buildCompatibilityResponse } from "./data/components";
import { DEMO_PERSONAS } from "./data/personas";
import { DEMO_APPROVALS, DEMO_FEEDBACK, DEMO_AUDIT } from "./data/approvals";
import { DEMO_QA_RESULTS } from "./data/qa-results";
import { DEMO_BUILDS } from "./data/builds";
import {
  DEMO_KNOWLEDGE_DOCUMENTS,
  DEMO_KNOWLEDGE_TAGS,
  DEMO_KNOWLEDGE_DOMAINS,
  DEMO_KNOWLEDGE_CONTENT,
} from "./data/knowledge";
import { DEMO_DESIGN_CONNECTIONS, DEMO_DESIGN_TOKENS } from "./data/design-sync";
import { DEMO_BRIEF_CONNECTIONS, DEMO_BRIEF_ITEMS, DEMO_BRIEF_DETAILS } from "./data/briefs";
import { DEMO_BRAND_CONFIG } from "./data/brand";
import { DEMO_GENERATED_IMAGES } from "./data/image-gen";
import { DEMO_TRANSLATIONS, DEMO_LOCALES } from "./data/locales";
import {
  DEMO_RENDERING_TESTS,
  DEMO_RENDERING_COMPARISON,
} from "./data/renderings";
import { DEMO_EMAIL_CLIENTS } from "./data/email-clients";
import { DEMO_COMPATIBILITY_BRIEF } from "./data/compatibility-brief";
import { DEMO_BLUEPRINT_RUN } from "./data/blueprint-run";
import { DEMO_BLUEPRINT_RUNS } from "./data/blueprint-runs";
import { DEMO_FAILURE_PATTERNS, DEMO_FAILURE_PATTERN_STATS } from "./data/failure-patterns";
import { demoStore } from "./demo-store";

function paginate<T>(items: T[], url: URL): { items: T[]; total: number; page: number; page_size: number } {
  const page = parseInt(url.searchParams.get("page") || "1", 10);
  const pageSize = parseInt(url.searchParams.get("page_size") || "20", 10);
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    total: items.length,
    page,
    page_size: pageSize,
  };
}

function filterBySearch<T extends { name: string }>(items: T[], search: string | null): T[] {
  if (!search) return items;
  const q = search.toLowerCase();
  return items.filter((item) => item.name.toLowerCase().includes(q));
}

/** Parse a regex capture group as integer (safe from undefined). */
function matchId(m: RegExpMatchArray, group: number): number {
  return parseInt(m[group] ?? "0", 10);
}

export function resolveDemo(urlStr: string): unknown | null {
  // Normalise: strip base URL if present, parse as URL
  const path = urlStr.replace(/^https?:\/\/[^/]+/, "");
  const url = new URL(path, "http://localhost");
  const p = url.pathname;

  // ── Orgs ──
  if (p === "/api/v1/orgs") {
    return paginate(DEMO_ORGS, url);
  }

  // ── Projects ──
  if (p === "/api/v1/projects") {
    const search = url.searchParams.get("search");
    const allProjects = [...DEMO_PROJECTS, ...demoStore.allProjects()];
    return paginate(filterBySearch(allProjects, search), url);
  }
  let m: RegExpMatchArray | null;

  m = p.match(/^\/api\/v1\/projects\/(\d+)$/);
  if (m) {
    const id = matchId(m, 1);
    return DEMO_PROJECTS.find((proj) => proj.id === id) ?? demoStore.findProject(id) ?? null;
  }

  // ── Templates ──
  m = p.match(/^\/api\/v1\/projects\/(\d+)\/templates$/);
  if (m) {
    const projectId = matchId(m, 1);
    const search = url.searchParams.get("search");
    const status = url.searchParams.get("status");
    let templates = [
      ...DEMO_TEMPLATES.filter((t) => t.project_id === projectId),
      ...demoStore.templatesForProject(projectId),
    ];
    if (search) templates = filterBySearch(templates, search);
    if (status) templates = templates.filter((t) => t.status === status);
    return paginate(templates, url);
  }
  m = p.match(/^\/api\/v1\/templates\/(\d+)$/);
  if (m) {
    const id = matchId(m!, 1);
    return DEMO_TEMPLATES.find((t) => t.id === id) ?? demoStore.findTemplate(id) ?? null;
  }
  m = p.match(/^\/api\/v1\/templates\/(\d+)\/versions$/);
  if (m) {
    const templateId = matchId(m, 1);
    const staticVersions = DEMO_VERSIONS.filter((v) => v.template_id === templateId);
    const runtimeVersions = demoStore.versionsForTemplate(templateId);
    return [...staticVersions, ...runtimeVersions];
  }
  m = p.match(/^\/api\/v1\/templates\/(\d+)\/versions\/(\d+)$/);
  if (m) {
    const templateId = matchId(m, 1);
    const versionNum = matchId(m, 2);
    return (
      DEMO_VERSIONS.find(
        (v) => v.template_id === templateId && v.version_number === versionNum,
      ) ??
      demoStore.findVersion(templateId, versionNum) ??
      null
    );
  }

  // ── Components ──
  if (p === "/api/v1/components/" || p === "/api/v1/components") {
    const search = url.searchParams.get("search");
    const category = url.searchParams.get("category");
    let comps = [...DEMO_COMPONENTS];
    if (search) comps = filterBySearch(comps, search);
    if (category) comps = comps.filter((c) => c.category === category);
    return paginate(comps, url);
  }
  m = p.match(/^\/api\/v1\/components\/(\d+)$/);
  if (m) {
    return DEMO_COMPONENTS.find((c) => c.id === matchId(m!, 1)) ?? null;
  }
  m = p.match(/^\/api\/v1\/components\/(\d+)\/compatibility$/);
  if (m) {
    return buildCompatibilityResponse(matchId(m!, 1));
  }
  m = p.match(/^\/api\/v1\/components\/(\d+)\/versions$/);
  if (m) {
    return DEMO_COMPONENT_VERSIONS.filter((v) => v.component_id === matchId(m!, 1));
  }

  // ── Personas ──
  if (p === "/api/v1/personas") {
    return DEMO_PERSONAS;
  }
  m = p.match(/^\/api\/v1\/personas\/(\d+)$/);
  if (m) {
    return DEMO_PERSONAS.find((persona) => persona.id === matchId(m!, 1)) ?? null;
  }

  // ── Approvals ──
  if (p === "/api/v1/approvals/" || p === "/api/v1/approvals") {
    const projectId = url.searchParams.get("project_id");
    if (projectId) {
      return DEMO_APPROVALS.filter((a) => a.project_id === parseInt(projectId, 10));
    }
    return DEMO_APPROVALS;
  }
  m = p.match(/^\/api\/v1\/approvals\/(\d+)$/);
  if (m) {
    return DEMO_APPROVALS.find((a) => a.id === matchId(m!, 1)) ?? null;
  }
  m = p.match(/^\/api\/v1\/approvals\/(\d+)\/feedback$/);
  if (m) {
    return DEMO_FEEDBACK[matchId(m, 1)] ?? [];
  }
  m = p.match(/^\/api\/v1\/approvals\/(\d+)\/audit$/);
  if (m) {
    return DEMO_AUDIT[matchId(m, 1)] ?? [];
  }

  // ── QA Results ──
  if (p === "/api/v1/qa/results") {
    const templateVersionId = url.searchParams.get("template_version_id");
    const passedParam = url.searchParams.get("passed");
    let results = [...DEMO_QA_RESULTS];
    if (templateVersionId) {
      const tvId = parseInt(templateVersionId, 10);
      results = results.filter((r) => r.template_version_id === tvId);
    }
    if (passedParam !== null) {
      const passed = passedParam === "true";
      results = results.filter((r) => r.passed === passed);
    }
    return paginate(results, url);
  }
  if (p === "/api/v1/qa/results/latest") {
    const tvId = url.searchParams.get("template_version_id");
    if (tvId) {
      const id = parseInt(tvId, 10);
      const matching = DEMO_QA_RESULTS.filter((r) => r.template_version_id === id);
      return matching[0] ?? null;
    }
    return DEMO_QA_RESULTS[0] ?? null;
  }
  m = p.match(/^\/api\/v1\/qa\/results\/(\d+)$/);
  if (m) {
    return DEMO_QA_RESULTS.find((r) => r.id === matchId(m!, 1)) ?? null;
  }

  // ── Builds ──
  m = p.match(/^\/api\/v1\/email\/builds\/(\d+)$/);
  if (m) {
    return DEMO_BUILDS.find((b) => b.id === matchId(m!, 1)) ?? null;
  }

  // ── Knowledge ──
  if (p === "/api/v1/knowledge/documents") {
    const domain = url.searchParams.get("domain");
    const tag = url.searchParams.get("tag");
    let docs = [...DEMO_KNOWLEDGE_DOCUMENTS];
    if (domain) docs = docs.filter((d) => d.domain === domain);
    if (tag) docs = docs.filter((d) => (d.tags ?? []).some((dt) => dt.name === tag));
    return paginate(docs, url);
  }

  m = p.match(/^\/api\/v1\/knowledge\/documents\/(\d+)$/);
  if (m) {
    return DEMO_KNOWLEDGE_DOCUMENTS.find((d) => d.id === matchId(m!, 1)) ?? null;
  }

  m = p.match(/^\/api\/v1\/knowledge\/documents\/(\d+)\/content$/);
  if (m) {
    return DEMO_KNOWLEDGE_CONTENT[matchId(m, 1)] ?? null;
  }

  if (p === "/api/v1/knowledge/domains") {
    return { domains: DEMO_KNOWLEDGE_DOMAINS, total: DEMO_KNOWLEDGE_DOMAINS.length };
  }

  if (p === "/api/v1/knowledge/tags") {
    return { tags: DEMO_KNOWLEDGE_TAGS, total: DEMO_KNOWLEDGE_TAGS.length };
  }

  // ── Design Sync Connections ──
  if (p === "/api/v1/design-sync/connections") {
    return DEMO_DESIGN_CONNECTIONS;
  }
  m = p.match(/^\/api\/v1\/design-sync\/connections\/(\d+)$/);
  if (m) {
    return DEMO_DESIGN_CONNECTIONS.find((c) => c.id === matchId(m!, 1)) ?? null;
  }
  m = p.match(/^\/api\/v1\/design-sync\/connections\/(\d+)\/tokens$/);
  if (m) {
    return DEMO_DESIGN_TOKENS[matchId(m, 1)] ?? null;
  }

  // ── Project Images ──
  m = p.match(/^\/api\/v1\/projects\/(\d+)\/images$/);
  if (m) {
    return DEMO_GENERATED_IMAGES[matchId(m, 1)] ?? [];
  }

  // ── Brand Config ──
  m = p.match(/^\/api\/v1\/orgs\/(\d+)\/brand$/);
  if (m) {
    return DEMO_BRAND_CONFIG[matchId(m, 1)] ?? null;
  }

  // ── Brief Connections ──
  if (p === "/api/v1/briefs/connections") {
    return DEMO_BRIEF_CONNECTIONS;
  }
  // All brief items (unified view across connections)
  if (p === "/api/v1/briefs/items") {
    let allItems = Object.values(DEMO_BRIEF_ITEMS).flat();
    const platformFilter = url.searchParams.get("platform");
    if (platformFilter) {
      allItems = allItems.filter((item) => item.platform === platformFilter);
    }
    const statusFilter = url.searchParams.get("status");
    if (statusFilter) {
      allItems = allItems.filter((item) => item.status === statusFilter);
    }
    const searchQuery = url.searchParams.get("search");
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      allItems = allItems.filter((item) => item.title.toLowerCase().includes(q));
    }
    return allItems;
  }
  m = p.match(/^\/api\/v1\/briefs\/connections\/(\d+)$/);
  if (m) {
    return DEMO_BRIEF_CONNECTIONS.find((c) => c.id === matchId(m!, 1)) ?? null;
  }
  m = p.match(/^\/api\/v1\/briefs\/connections\/(\d+)\/items$/);
  if (m) {
    return DEMO_BRIEF_ITEMS[matchId(m, 1)] ?? [];
  }
  m = p.match(/^\/api\/v1\/briefs\/items\/(\d+)$/);
  if (m) {
    return DEMO_BRIEF_DETAILS[matchId(m, 1)] ?? null;
  }

  // ── Renderings (aligned with /api/v1/rendering/) ──
  if (p === "/api/v1/rendering/tests") {
    const statusFilter = url.searchParams.get("status");
    let tests = [...DEMO_RENDERING_TESTS];
    if (statusFilter) tests = tests.filter((t) => t.status === statusFilter);
    return paginate(tests, url);
  }
  m = p.match(/^\/api\/v1\/rendering\/tests\/(\d+)$/);
  if (m) {
    return DEMO_RENDERING_TESTS.find((t) => t.id === matchId(m!, 1)) ?? null;
  }

  // ── Translations ──
  if (p === "/api/v1/translations") {
    return DEMO_TRANSLATIONS;
  }

  // ── Locales ──
  if (p === "/api/v1/locales") {
    return DEMO_LOCALES;
  }

  // ── Ontology: Email Clients ──
  if (p === "/api/v1/ontology/clients") {
    return DEMO_EMAIL_CLIENTS;
  }

  // ── Project Compatibility Brief ──
  m = p.match(/^\/api\/v1\/projects\/\d+\/compatibility-brief$/);
  if (m) {
    return DEMO_COMPATIBILITY_BRIEF;
  }

  // ── Blueprint Runs (history) ──
  m = p.match(/^\/api\/v1\/projects\/(\d+)\/blueprint-runs$/);
  if (m) {
    const projectId = matchId(m, 1);
    const statusFilter = url.searchParams.get("status");
    let runs = DEMO_BLUEPRINT_RUNS.filter((r) => r.project_id === projectId);
    if (statusFilter) runs = runs.filter((r) => r.status === statusFilter);
    return paginate(runs, url);
  }
  m = p.match(/^\/api\/v1\/blueprint-runs\/(\d+)$/);
  if (m) {
    return DEMO_BLUEPRINT_RUNS.find((r) => r.id === matchId(m!, 1)) ?? null;
  }

  // ── Blueprint Run (POST simulated as GET for demo) ──
  if (p === "/api/v1/blueprints/run") {
    return DEMO_BLUEPRINT_RUN;
  }

  // ── Failure Patterns ──
  if (p === "/api/v1/blueprints/failure-patterns/stats") {
    return DEMO_FAILURE_PATTERN_STATS;
  }
  if (p === "/api/v1/blueprints/failure-patterns") {
    let patterns = [...DEMO_FAILURE_PATTERNS];
    const agentFilter = url.searchParams.get("agent_name");
    if (agentFilter) patterns = patterns.filter((fp) => fp.agent_name === agentFilter);
    const checkFilter = url.searchParams.get("qa_check");
    if (checkFilter) patterns = patterns.filter((fp) => fp.qa_check === checkFilter);
    const clientFilter = url.searchParams.get("client_id");
    if (clientFilter) patterns = patterns.filter((fp) => fp.client_ids.includes(clientFilter));
    return paginate(patterns, url);
  }

  return null;
}
