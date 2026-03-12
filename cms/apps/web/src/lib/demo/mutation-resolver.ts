/**
 * Demo mode mutation resolver.
 * Handles POST/PATCH operations by returning realistic success responses.
 */

import type { QACheckResult, QAResultResponse } from "@/types/qa";
import { SPRING_SALE_HERO_HTML } from "./data/html-sources";
import { DEMO_KNOWLEDGE_DOCUMENTS } from "./data/knowledge";
import { DEMO_RENDERING_COMPARISON } from "./data/renderings";
import { buildDemoGraphSearchResults, buildDemoGraphCompletion } from "./data/graph-search";
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
          `${d.title ?? ""} ${d.description ?? ""} ${(d.tags ?? []).map((dt) => dt.name).join(" ")}`.toLowerCase();
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

  // Graph knowledge search
  if (p === "/api/v1/knowledge/graph/search") {
    const body = _body as Record<string, unknown> | null;
    const query = (body?.query as string | undefined) ?? "";
    const mode = (body?.mode as string | undefined) ?? "chunks";
    const topK = (body?.top_k as number | undefined) ?? 10;

    if (mode === "completion") {
      return {
        results: [
          {
            content: buildDemoGraphCompletion(query),
            entities: [],
            relationships: [],
            score: 1.0,
          },
        ],
        query,
        mode: "completion",
      };
    }

    return {
      results: buildDemoGraphSearchResults(query, topK),
      query,
      mode: "chunks",
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

  // Design sync connection create
  if (p === "/api/v1/design-sync/connections") {
    const body = _body as Record<string, unknown> | null;
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      name: body?.name ?? "New Connection",
      provider: body?.provider ?? "figma",
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

  // Design sync connection delete
  if (p === "/api/v1/design-sync/connections/delete") {
    return { success: true };
  }

  // Design sync connection sync
  if (p === "/api/v1/design-sync/connections/sync") {
    const body = _body as Record<string, unknown> | null;
    return {
      id: body?.id ?? 1,
      name: "Synced Connection",
      provider: "figma",
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

  // Rendering test (aligned with backend schema)
  if (p === "/api/v1/rendering/tests") {
    const body = _body as Record<string, unknown> | null;
    const clientNames = [
      "Gmail", "Outlook 365", "Apple Mail macOS", "iPhone 16 Mail",
      "Yahoo Mail", "Thunderbird", "Samsung Mail", "Gmail Android",
      "Outlook.com", "iOS Dark Mode", "Gmail iOS", "Outlook Mac",
      "Gmail Workspace", "ProtonMail", "iPad Mail", "Outlook iOS",
      "Outlook Android", "iPhone 15 Mail", "Yahoo Mobile", "Fastmail",
    ];
    const requestedCount = (body?.clients as string[] | undefined)?.length ?? 20;
    const screenshots = clientNames.slice(0, requestedCount).map((name) => {
      const h = Math.random();
      return {
        client_name: name,
        screenshot_url: `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="600" height="400" fill="#f0f0f0"/><text x="300" y="200" text-anchor="middle" fill="#999" font-family="sans-serif">${name}</text></svg>`)}`,
        os: name.includes("iPhone") || name.includes("iPad") || name.includes("iOS") ? "ios" : name.includes("Android") || name.includes("Samsung") ? "android" : name.includes("Outlook 2") || name.includes("365") || name.includes("Windows") ? "windows" : "web",
        category: name.includes("iPhone") || name.includes("iPad") || name.includes("Android") || name.includes("Samsung") ? "mobile" : name.includes("Gmail") || name.includes("Yahoo") || name.includes("Proton") || name.includes("Fast") || name.includes(".com") || name.includes("Zoho") ? "web" : name.includes("Dark") ? "dark_mode" : "desktop",
        status: (h < 0.1 ? "failed" : "complete") as "pending" | "complete" | "failed",
      };
    });
    const completedCount = screenshots.filter((s) => s.status === "complete").length;
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      external_test_id: `demo_${Date.now().toString(36)}`,
      provider: "litmus",
      status: "complete",
      build_id: (body?.build_id as number) ?? null,
      template_version_id: (body?.template_version_id as number) ?? null,
      clients_requested: requestedCount,
      clients_completed: completedCount,
      screenshots,
      created_at: new Date().toISOString(),
    };
  }

  // Rendering comparison (POST-based)
  if (p === "/api/v1/rendering/compare") {
    return DEMO_RENDERING_COMPARISON;
  }

  // Brief import
  if (p === "/api/v1/briefs/import") {
    return {
      project_id: Math.floor(Math.random() * 10000) + 100,
    };
  }

  return null;
}
