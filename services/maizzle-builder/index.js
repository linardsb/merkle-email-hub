/**
 * Maizzle Builder Service
 *
 * Express server that receives email template source + config via HTTP,
 * runs CSS optimization (PostCSS email plugin + Lightning CSS) then
 * Maizzle's build programmatically, and returns compiled HTML.
 *
 * Called by the FastAPI backend (app/email_engine/) via HTTP POST.
 */

import express from "express";
import { render } from "@maizzle/framework";
import postcss from "postcss";
import emailOptimize, { loadOntology } from "./postcss-email-optimize.js";
import { transform } from "lightningcss";
import { isPreCompiledEmail } from "./precompiled-detect.js";

const app = express();
const PORT = process.env.PORT || 3001;
app.use(express.json({ limit: "5mb" }));

let ontologyVersion = null;
try {
  ontologyVersion = loadOntology().version;
  console.log(`Ontology loaded: ${ontologyVersion}`);
} catch (err) {
  console.warn(`Ontology not loaded: ${err.message}`);
}

async function optimizeCss(html, targetClients) {
  const MSO_RE = /<!--\[if\s+mso.*?\]>.*?<!\[endif\]-->/gis;
  const msoMap = new Map();
  let idx = 0;
  let safe = html;
  for (const m of html.matchAll(MSO_RE)) {
    const ph = `__MSO_${idx++}__`;
    msoMap.set(ph, m[0]);
    safe = safe.replace(m[0], ph);
  }

  const STYLE_RE = /<style[^>]*>([\s\S]*?)<\/style>/gi;
  const blocks = [];
  let match;
  while ((match = STYLE_RE.exec(safe)) !== null) blocks.push(match[1]);

  if (!blocks.length) {
    for (const [ph, orig] of msoMap) safe = safe.replace(ph, orig);
    return { optimizedHtml: safe, optimization: { removed_properties: [], conversions: [], warnings: [], original_css_size: 0, optimized_css_size: 0 } };
  }

  const allRemoved = [], allConversions = [], allWarnings = [];
  let origSize = 0, optSize = 0;
  const optimized = [];

  for (const css of blocks) {
    origSize += Buffer.byteLength(css, 'utf-8');
    const r = await postcss([emailOptimize({ targetClients })]).process(css, { from: undefined });
    let out = r.css;
    try { out = transform({ filename: 'email.css', code: Buffer.from(out), minify: true }).code.toString(); } catch { /* minification is best-effort */ }
    optSize += Buffer.byteLength(out, 'utf-8');
    optimized.push(out);
    if (r.emailOptimization) {
      allRemoved.push(...r.emailOptimization.removed_properties);
      allConversions.push(...r.emailOptimization.conversions);
      allWarnings.push(...r.emailOptimization.warnings);
    }
  }

  let bi = 0;
  let result = safe.replace(STYLE_RE, () => `<style>${optimized[bi++] || ''}</style>`);
  for (const [ph, orig] of msoMap) result = result.replace(ph, orig);

  return { optimizedHtml: result, optimization: { removed_properties: allRemoved, conversions: allConversions, warnings: allWarnings, original_css_size: origSize, optimized_css_size: optSize } };
}

app.get("/health", (_req, res) => {
  res.json({ status: "healthy", service: "maizzle-builder", ontology_version: ontologyVersion });
});

app.post("/build", async (req, res) => {
  const start = Date.now();
  const { source, config = {}, production = false, target_clients } = req.body;
  if (!source) return res.status(400).json({ error: "source is required" });

  try {
    let html = source;
    let optimization = null;
    if (ontologyVersion && target_clients?.length) {
      const r = await optimizeCss(html, target_clients);
      html = r.optimizedHtml;
      optimization = r.optimization;
    }

    const passthrough = isPreCompiledEmail(html);

    if (passthrough) {
      res.json({
        html,
        build_time_ms: Date.now() - start,
        passthrough: true,
        ...(optimization && { optimization }),
      });
      return;
    }

    const maizzleConfig = { ...config, build: { content: [], ...(config.build || {}) } };
    if (production) {
      maizzleConfig.inlineCSS = { enabled: true };
      maizzleConfig.prettify = false;
      maizzleConfig.minify = { collapseWhitespace: true, removeComments: true };
    }

    const rendered = await render(html, { maizzle: maizzleConfig });
    res.json({
      html: rendered.html,
      build_time_ms: Date.now() - start,
      passthrough: false,
      ...(optimization && { optimization }),
    });
  } catch (err) {
    console.error("Build failed:", err.message);
    res.status(500).json({ error: "Build failed", detail: err.message, build_time_ms: Date.now() - start });
  }
});

app.post("/preview", async (req, res) => {
  const start = Date.now();
  const { source, config = {}, target_clients } = req.body;
  if (!source) return res.status(400).json({ error: "source is required" });

  try {
    let html = source;
    let optimization = null;
    if (ontologyVersion && target_clients?.length) {
      const r = await optimizeCss(html, target_clients);
      html = r.optimizedHtml;
      optimization = r.optimization;
    }

    const passthrough = isPreCompiledEmail(html);

    if (passthrough) {
      res.json({
        html,
        build_time_ms: Date.now() - start,
        passthrough: true,
        ...(optimization && { optimization }),
      });
      return;
    }

    const rendered = await render(html, { maizzle: { ...config, inlineCSS: { enabled: true }, prettify: true } });
    res.json({
      html: rendered.html,
      build_time_ms: Date.now() - start,
      passthrough: false,
      ...(optimization && { optimization }),
    });
  } catch (err) {
    console.error("Preview failed:", err.message);
    res.status(500).json({ error: "Preview failed", detail: err.message, build_time_ms: Date.now() - start });
  }
});

app.listen(PORT, () => console.log(`Maizzle builder listening on port ${PORT}`));
