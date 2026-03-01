/**
 * Demo mode mutation resolver.
 * Handles POST/PATCH operations by returning realistic success responses.
 */

import type { QACheckResult, QAResultResponse } from "@/types/qa";
import { SPRING_SALE_HERO_HTML } from "./data/html-sources";
import { DEMO_KNOWLEDGE_DOCUMENTS } from "./data/knowledge";

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
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      project_id: 1,
      name: "New Template",
      description: null,
      subject_line: null,
      preheader_text: null,
      status: "draft",
      created_by_id: 1,
      latest_version: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // Save version
  if (p.match(/^\/api\/v1\/templates\/\d+\/versions$/)) {
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      template_id: 1,
      version_number: 1,
      html_source: "",
      css_source: null,
      changelog: "Demo save",
      created_by_id: 1,
      created_at: new Date().toISOString(),
    };
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
    return {
      id: Math.floor(Math.random() * 10000) + 100,
      build_id: 1,
      connector_type: "raw_html",
      status: "completed",
      external_id: null,
      error_message: null,
      created_at: new Date().toISOString(),
    };
  }

  return null;
}
