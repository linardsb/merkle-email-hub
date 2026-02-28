/**
 * Maizzle Builder Service
 *
 * Thin Express server that receives email template source + config via HTTP,
 * runs Maizzle's build programmatically, and returns compiled HTML.
 *
 * Called by the FastAPI backend (app/email_engine/) via HTTP POST.
 */

import express from "express";
import { render } from "@maizzle/framework";

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json({ limit: "5mb" }));

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "healthy", service: "maizzle-builder" });
});

/**
 * POST /build
 * Body: { source: string, config?: object, production?: boolean }
 * Returns: { html: string, build_time_ms: number }
 */
app.post("/build", async (req, res) => {
  const start = Date.now();
  const { source, config = {}, production = false } = req.body;

  if (!source) {
    return res.status(400).json({ error: "source is required" });
  }

  try {
    const maizzleConfig = {
      ...config,
      build: {
        content: [],
        ...(config.build || {}),
      },
    };

    if (production) {
      maizzleConfig.inlineCSS = { enabled: true };
      maizzleConfig.prettify = false;
      maizzleConfig.minify = {
        collapseWhitespace: true,
        removeComments: true,
      };
    }

    const { html } = await render(source, {
      maizzle: maizzleConfig,
    });

    const buildTimeMs = Date.now() - start;

    res.json({
      html,
      build_time_ms: buildTimeMs,
    });
  } catch (err) {
    console.error("Build failed:", err.message);
    res.status(500).json({
      error: "Build failed",
      detail: err.message,
      build_time_ms: Date.now() - start,
    });
  }
});

/**
 * POST /preview
 * Same as /build but with development-friendly defaults.
 */
app.post("/preview", async (req, res) => {
  const start = Date.now();
  const { source, config = {} } = req.body;

  if (!source) {
    return res.status(400).json({ error: "source is required" });
  }

  try {
    const { html } = await render(source, {
      maizzle: {
        ...config,
        inlineCSS: { enabled: true },
        prettify: true,
      },
    });

    res.json({
      html,
      build_time_ms: Date.now() - start,
    });
  } catch (err) {
    console.error("Preview failed:", err.message);
    res.status(500).json({
      error: "Preview failed",
      detail: err.message,
      build_time_ms: Date.now() - start,
    });
  }
});

app.listen(PORT, () => {
  console.log(`Maizzle builder listening on port ${PORT}`);
});
