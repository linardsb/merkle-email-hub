/**
 * Demo mode mutation resolver.
 * Handles POST/PATCH operations by returning realistic success responses.
 */

import type { QACheckResult, QAResultResponse } from "@/types/qa";
import { SPRING_SALE_HERO_HTML } from "./data/html-sources";
import { DEMO_KNOWLEDGE_DOCUMENTS } from "./data/knowledge";
import { demoStore } from "./demo-store";

const CHECK_NAMES = [
  "html_validation",
  "css_support",
  "file_size",
  "link_validation",
  "spam_score",
  "dark_mode",
  "accessibility",
  "fallback",
  "image_optimization",
  "brand_compliance",
] as const;

function randomQAResult(): QAResultResponse {
  const checks: QACheckResult[] = CHECK_NAMES.map((name) => {
    const passed = Math.random() > 0.25;
    return {
      check_name: name,
      passed,
      score: passed ? 1 : 0,
      details: passed ? null : `Demo: ${name.replace(/_/g, " ")} check failed`,
      severity: passed ? "info" : "warning",
    };
  });

  const checksPassed = checks.filter((c) => c.passed).length;
  const overall = checksPassed / checks.length;

  return {
    id: Math.floor(Math.random() * 10000) + 100,
    build_id: 1,
    template_version_id: 101,
    overall_score: overall,
    passed: overall >= 0.7,
    checks_passed: checksPassed,
    checks_total: checks.length,
    checks,
    override: null,
    created_at: new Date().toISOString(),
  };
}

export function resolveDemoMutation(urlStr: string, _body: unknown): unknown | null {
  const path = urlStr.replace(/^https?:\/\/[^/]+/, "");
  const p = new URL(path, "http://localhost").pathname;

  // QA Run
  if (p === "/api/v1/qa/run") {
    return randomQAResult();
  }

  // Email build
  if (p === "/api/v1/email/build") {
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      project_id: 1,
      template_name: "Demo Build",
      status: "completed",
      compiled_html: SPRING_SALE_HERO_HTML,
      error_message: null,
      is_production: false,
      created_at: new Date().toISOString(),
    };
  }

  // Email preview — return the posted source HTML as the "compiled" output
  if (p === "/api/v1/email/preview") {
    const body = _body as Record<string, unknown> | null;
    const sourceHtml =
      body && typeof body.source_html === "string"
        ? body.source_html
        : SPRING_SALE_HERO_HTML;
    return {
      compiled_html: sourceHtml,
      build_time_ms: 120 + Math.floor(Math.random() * 80),
    };
  }

  // Create template
  if (p.match(/^\/api\/v1\/projects\/\d+\/templates$/)) {
    const projectId = parseInt(p.match(/\/projects\/(\d+)\//)![1]!, 10);
    const body = _body as Record<string, unknown> | null;
    const template = {
      id: Math.floor(Math.random() * 10000) + 100,
      project_id: projectId,
      name: (body?.name as string) ?? "New Template",
      description: null,
      subject_line: null,
      preheader_text: null,
      status: "draft",
      created_by_id: 1,
      latest_version: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    demoStore.addTemplate(template as any);
    return template;
  }

  // Save version
  if (p.match(/^\/api\/v1\/templates\/\d+\/versions$/)) {
    const templateId = parseInt(p.match(/\/templates\/(\d+)\//)![1]!, 10);
    const body = _body as Record<string, unknown> | null;
    const existingVersions = demoStore.versionsForTemplate(templateId);
    const nextVersion = existingVersions.length + 1;
    const version = {
      id: Math.floor(Math.random() * 10000) + 100,
      template_id: templateId,
      version_number: nextVersion,
      html_source: (body?.html_source as string) ?? "",
      css_source: null,
      changelog: `v${nextVersion} save`,
      created_by_id: 1,
      created_at: new Date().toISOString(),
    };
    demoStore.addVersion(version as any);
    return version;
  }

  // Create approval
  if (p === "/api/v1/approvals/" || p === "/api/v1/approvals") {
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      build_id: 1,
      project_id: 1,
      status: "pending",
      requested_by_id: 1,
      reviewed_by_id: null,
      review_note: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // Approval decide
  if (p.match(/^\/api\/v1\/approvals\/\d+\/decide$/)) {
    return {
      id: 1,
      build_id: 1,
      project_id: 1,
      status: "approved",
      requested_by_id: 1,
      reviewed_by_id: 1,
      review_note: "Demo approval",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // Add feedback
  if (p.match(/^\/api\/v1\/approvals\/\d+\/feedback$/)) {
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      approval_id: 1,
      author_id: 1,
      content: "Demo feedback",
      feedback_type: "comment",
      created_at: new Date().toISOString(),
    };
  }

  // QA override
  if (p.match(/^\/api\/v1\/qa\/results\/\d+\/override$/)) {
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      qa_result_id: 1,
      overridden_by_id: 1,
      justification: "Demo override",
      checks_overridden: ["dark_mode"],
      created_at: new Date().toISOString(),
    };
  }

  // Knowledge search
  if (p === "/api/v1/knowledge/search") {
    const body = _body as Record<string, unknown> | null;
    const query = (body?.query as string | undefined)?.toLowerCase() ?? "";
    const domain = body?.domain as string | undefined;
    const limit = (body?.limit as number | undefined) ?? 10;

    let docs = [...DEMO_KNOWLEDGE_DOCUMENTS];
    if (domain) docs = docs.filter((d) => d.domain === domain);

    const results = docs
      .filter((d) => {
        const text =
          `${d.title ?? ""} ${d.description ?? ""} ${d.tags.map((dt) => dt.name).join(" ")}`.toLowerCase();
        return text.includes(query);
      })
      .slice(0, limit)
      .map((d, i) => ({
        chunk_content: `${d.description ?? d.title ?? d.filename}. This document covers ${d.domain.replace(/_/g, " ")} topics relevant to your search.`,
        document_id: d.id,
        document_filename: d.filename,
        domain: d.domain,
        language: d.language,
        chunk_index: 0,
        score: Math.round((0.95 - i * 0.07) * 100) / 100,
        metadata_json: null,
      }));

    return {
      results,
      query: body?.query ?? "",
      total_candidates: results.length * 3,
      reranked: true,
    };
  }

  // Connector export
  if (p === "/api/v1/connectors/export") {
    const body = _body as Record<string, unknown> | null;
    const connectorType = (body?.connector_type as string) ?? "braze";
    const name = (body?.content_block_name as string) ?? "export";
    const prefix = { braze: "braze_cb", sfmc: "sfmc_ca", adobe_campaign: "adobe_dl", taxi: "taxi_tpl" }[connectorType] ?? connectorType;
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      build_id: body?.build_id ?? 1,
      connector_type: connectorType,
      status: "success",
      external_id: `${prefix}_${name.toLowerCase().replace(/\s+/g, "_")}`,
      error_message: null,
      created_at: new Date().toISOString(),
    };
  }

  // Create project
  if (p === "/api/v1/projects") {
    const body = _body as Record<string, unknown> | null;
    const project = {
      id: Math.floor(Math.random() * 10000) + 100,
      name: (body?.name as string) ?? "New Project",
      description: (body?.description as string) ?? null,
      client_org_id: (body?.client_org_id as number) ?? 1,
      status: "draft",
      created_by_id: 1,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    demoStore.addProject(project as any);
    return project;
  }

  // Figma connection create
  if (p === "/api/v1/figma/connections") {
    const body = _body as Record<string, unknown> | null;
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      name: body?.name ?? "New Connection",
      file_key: "demoFileKey" + Math.floor(Math.random() * 1000),
      file_url: body?.file_url ?? "",
      access_token_last4: (body?.access_token as string)?.slice(-4) ?? "demo",
      status: "connected",
      last_synced_at: new Date().toISOString(),
      project_id: body?.project_id ?? null,
      project_name: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // Figma connection delete
  if (p === "/api/v1/figma/connections/delete") {
    return { success: true };
  }

  // Figma connection sync
  if (p === "/api/v1/figma/connections/sync") {
    const body = _body as Record<string, unknown> | null;
    return {
      id: body?.id ?? 1,
      name: "Synced Connection",
      file_key: "syncedKey",
      file_url: "",
      access_token_last4: "sync",
      status: "connected",
      last_synced_at: new Date().toISOString(),
      project_id: null,
      project_name: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // Create persona
  if (p === "/api/v1/personas") {
    const body = _body as Record<string, unknown> | null;
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      name: body?.name ?? "Custom Persona",
      slug: body?.slug ?? "custom-persona",
      description: body?.description ?? null,
      email_client: body?.email_client ?? "gmail",
      device_type: body?.device_type ?? "desktop",
      dark_mode: body?.dark_mode ?? false,
      viewport_width: body?.viewport_width ?? 600,
      os_name: body?.os_name ?? "macOS",
      is_preset: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // Image generation
  if (p === "/api/v1/images/generate") {
    const body = _body as Record<string, unknown> | null;
    const seed = Math.floor(Math.random() * 10000);
    return {
      image: {
        id: Math.floor(Math.random() * 10000) + 100,
        url: `https://picsum.photos/seed/${seed}/600/400`,
        prompt: body?.prompt ?? "Generated image",
        style: body?.style ?? "product",
        aspect_ratio: body?.aspect_ratio ?? "4:3",
        width: 600,
        height: 400,
        created_at: new Date().toISOString(),
      },
    };
  }

  // Brand config update
  if (p === "/api/v1/orgs/brand") {
    const body = _body as Record<string, unknown> | null;
    return {
      org_id: body?.org_id ?? 1,
      colors: body?.colors ?? [],
      typography: body?.typography ?? [],
      logoRules: body?.logoRules ?? null,
      forbiddenPatterns: body?.forbiddenPatterns ?? [],
      updated_at: new Date().toISOString(),
    };
  }

  // Brief connection create
  if (p === "/api/v1/briefs/connections") {
    const body = _body as Record<string, unknown> | null;
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      name: body?.name ?? "New Connection",
      platform: body?.platform ?? "jira",
      status: "connected",
      project_url: body?.project_url ?? "",
      credential_last4: "demo",
      project_id: body?.project_id ?? null,
      project_name: null,
      last_synced_at: new Date().toISOString(),
      items_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // Brief connection delete
  if (p === "/api/v1/briefs/connections/delete") {
    return { success: true };
  }

  // Brief connection sync
  if (p === "/api/v1/briefs/connections/sync") {
    const body = _body as Record<string, unknown> | null;
    return {
      id: body?.id ?? 1,
      name: "Synced Connection",
      platform: "jira",
      status: "connected",
      project_url: "",
      credential_last4: "sync",
      project_id: null,
      project_name: null,
      last_synced_at: new Date().toISOString(),
      items_count: 4,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // Brief import
  if (p === "/api/v1/briefs/import") {
    return {
      project_id: Math.floor(Math.random() * 10000) + 100,
    };
  }

  return null;
}
