import type {
  KnowledgeDocument,
  KnowledgeTag,
  KnowledgeDocumentContent,
} from "@/types/knowledge";

// ── Tags ──

export const DEMO_KNOWLEDGE_TAGS: KnowledgeTag[] = [
  { id: 1, name: "css", created_at: "2026-01-15T10:00:00Z" },
  { id: 2, name: "layout", created_at: "2026-01-15T10:00:00Z" },
  { id: 3, name: "typography", created_at: "2026-01-15T10:00:00Z" },
  { id: 4, name: "colors", created_at: "2026-01-15T10:00:00Z" },
  { id: 5, name: "dark-mode", created_at: "2026-01-15T10:00:00Z" },
  { id: 6, name: "responsive", created_at: "2026-01-15T10:00:00Z" },
  { id: 7, name: "accessibility", created_at: "2026-01-15T10:00:00Z" },
  { id: 8, name: "outlook", created_at: "2026-01-15T10:00:00Z" },
  { id: 9, name: "gmail", created_at: "2026-01-15T10:00:00Z" },
  { id: 10, name: "vml", created_at: "2026-01-15T10:00:00Z" },
  { id: 11, name: "images", created_at: "2026-01-15T10:00:00Z" },
  { id: 12, name: "buttons", created_at: "2026-01-15T10:00:00Z" },
  { id: 13, name: "tables", created_at: "2026-01-15T10:00:00Z" },
  { id: 14, name: "media-queries", created_at: "2026-01-15T10:00:00Z" },
  { id: 15, name: "file-size", created_at: "2026-01-15T10:00:00Z" },
];

const t = (ids: number[]) =>
  ids.map((id) => DEMO_KNOWLEDGE_TAGS.find((tag) => tag.id === id)!);

// ── Domains ──

export const DEMO_KNOWLEDGE_DOMAINS: string[] = [
  "best_practices",
  "client_quirks",
  "css_support",
];

// ── Documents (20 total, matching seed manifest) ──

const base = {
  source_type: "text" as const,
  language: "en",
  status: "completed" as const,
  error_message: null,
  metadata_json: null,
  ocr_applied: false,
  has_file: true,
};

export const DEMO_KNOWLEDGE_DOCUMENTS: KnowledgeDocument[] = [
  // CSS Support (8)
  {
    ...base,
    id: 1,
    filename: "layout-properties.md",
    title: "CSS Layout Properties",
    description:
      "Flexbox, grid, and display compatibility across email clients",
    domain: "css_support",
    file_size_bytes: 4200,
    chunk_count: 12,
    tags: t([1, 2]),
    created_at: "2026-01-15T10:00:00Z",
    updated_at: "2026-01-15T10:00:00Z",
  },
  {
    ...base,
    id: 2,
    filename: "box-model.md",
    title: "Box Model Properties",
    description: "Margin, padding, width, and height support in email clients",
    domain: "css_support",
    file_size_bytes: 3800,
    chunk_count: 10,
    tags: t([1, 2]),
    created_at: "2026-01-15T10:05:00Z",
    updated_at: "2026-01-15T10:05:00Z",
  },
  {
    ...base,
    id: 3,
    filename: "typography.md",
    title: "Typography in Email",
    description:
      "Font families, web fonts, line-height, and text styling across clients",
    domain: "css_support",
    file_size_bytes: 5100,
    chunk_count: 14,
    tags: t([1, 3]),
    created_at: "2026-01-15T10:10:00Z",
    updated_at: "2026-01-15T10:10:00Z",
  },
  {
    ...base,
    id: 4,
    filename: "colors-backgrounds.md",
    title: "Colors & Backgrounds",
    description: "Color values, gradients, background properties, and opacity",
    domain: "css_support",
    file_size_bytes: 3500,
    chunk_count: 9,
    tags: t([1, 4]),
    created_at: "2026-01-15T10:15:00Z",
    updated_at: "2026-01-15T10:15:00Z",
  },
  {
    ...base,
    id: 5,
    filename: "borders-shadows.md",
    title: "Borders & Shadows",
    description: "Border-radius, box-shadow, and outline support",
    domain: "css_support",
    file_size_bytes: 2900,
    chunk_count: 8,
    tags: t([1]),
    created_at: "2026-01-15T10:20:00Z",
    updated_at: "2026-01-15T10:20:00Z",
  },
  {
    ...base,
    id: 6,
    filename: "media-queries.md",
    title: "Media Queries",
    description:
      "@media rules, prefers-color-scheme, and viewport-based queries",
    domain: "css_support",
    file_size_bytes: 4600,
    chunk_count: 11,
    tags: t([1, 14, 5]),
    created_at: "2026-01-15T10:25:00Z",
    updated_at: "2026-01-15T10:25:00Z",
  },
  {
    ...base,
    id: 7,
    filename: "selectors.md",
    title: "CSS Selectors",
    description: "Pseudo-classes, nth-child, attribute selectors in email",
    domain: "css_support",
    file_size_bytes: 3200,
    chunk_count: 9,
    tags: t([1]),
    created_at: "2026-01-15T10:30:00Z",
    updated_at: "2026-01-15T10:30:00Z",
  },
  {
    ...base,
    id: 8,
    filename: "dark-mode-css.md",
    title: "Dark Mode CSS",
    description:
      "color-scheme meta, prefers-color-scheme, data-ogsc/data-ogsb overrides",
    domain: "css_support",
    file_size_bytes: 5800,
    chunk_count: 15,
    tags: t([1, 5]),
    created_at: "2026-01-15T10:35:00Z",
    updated_at: "2026-01-15T10:35:00Z",
  },

  // Best Practices (6)
  {
    ...base,
    id: 9,
    filename: "table-based-layout.md",
    title: "Table-Based Layout",
    description: "Nested tables, layout patterns, and structural best practices",
    domain: "best_practices",
    file_size_bytes: 6200,
    chunk_count: 16,
    tags: t([13, 2]),
    created_at: "2026-01-16T10:00:00Z",
    updated_at: "2026-01-16T10:00:00Z",
  },
  {
    ...base,
    id: 10,
    filename: "responsive-email.md",
    title: "Responsive Email Design",
    description: "Fluid hybrid approach, mobile-first strategies, breakpoints",
    domain: "best_practices",
    file_size_bytes: 5500,
    chunk_count: 14,
    tags: t([6, 14]),
    created_at: "2026-01-16T10:05:00Z",
    updated_at: "2026-01-16T10:05:00Z",
  },
  {
    ...base,
    id: 11,
    filename: "image-optimization.md",
    title: "Image Optimization",
    description: "Image formats, dimensions, retina displays, and alt text",
    domain: "best_practices",
    file_size_bytes: 4100,
    chunk_count: 11,
    tags: t([11, 7]),
    created_at: "2026-01-16T10:10:00Z",
    updated_at: "2026-01-16T10:10:00Z",
  },
  {
    ...base,
    id: 12,
    filename: "cta-buttons.md",
    title: "CTA Buttons",
    description:
      "VML buttons, padding-based buttons, and bulletproof button patterns",
    domain: "best_practices",
    file_size_bytes: 3900,
    chunk_count: 10,
    tags: t([12, 10]),
    created_at: "2026-01-16T10:15:00Z",
    updated_at: "2026-01-16T10:15:00Z",
  },
  {
    ...base,
    id: 13,
    filename: "accessibility.md",
    title: "Email Accessibility",
    description:
      "WCAG AA compliance, alt text, contrast ratios, semantic structure",
    domain: "best_practices",
    file_size_bytes: 5300,
    chunk_count: 13,
    tags: t([7]),
    created_at: "2026-01-16T10:20:00Z",
    updated_at: "2026-01-16T10:20:00Z",
  },
  {
    ...base,
    id: 14,
    filename: "file-size-optimization.md",
    title: "File Size Optimization",
    description:
      "Gmail 102KB clipping, code minification, image compression strategies",
    domain: "best_practices",
    file_size_bytes: 3600,
    chunk_count: 9,
    tags: t([15, 9]),
    created_at: "2026-01-16T10:25:00Z",
    updated_at: "2026-01-16T10:25:00Z",
  },

  // Client Quirks (6)
  {
    ...base,
    id: 15,
    filename: "outlook-windows.md",
    title: "Outlook on Windows",
    description:
      "Word rendering engine, VML backgrounds, MSO conditionals, table issues",
    domain: "client_quirks",
    file_size_bytes: 7200,
    chunk_count: 18,
    tags: t([8, 10]),
    created_at: "2026-01-17T10:00:00Z",
    updated_at: "2026-01-17T10:00:00Z",
  },
  {
    ...base,
    id: 16,
    filename: "gmail.md",
    title: "Gmail Quirks",
    description:
      "CSS stripping, class renaming, image blocking, and AMP support",
    domain: "client_quirks",
    file_size_bytes: 5100,
    chunk_count: 13,
    tags: t([9, 1]),
    created_at: "2026-01-17T10:05:00Z",
    updated_at: "2026-01-17T10:05:00Z",
  },
  {
    ...base,
    id: 17,
    filename: "apple-mail-ios.md",
    title: "Apple Mail & iOS",
    description:
      "WebKit rendering, dark mode auto-inversion, dynamic type support",
    domain: "client_quirks",
    file_size_bytes: 4800,
    chunk_count: 12,
    tags: t([5]),
    created_at: "2026-01-17T10:10:00Z",
    updated_at: "2026-01-17T10:10:00Z",
  },
  {
    ...base,
    id: 18,
    filename: "yahoo-mail.md",
    title: "Yahoo Mail",
    description:
      "!important overrides, CSS stripping quirks, and attribute selectors",
    domain: "client_quirks",
    file_size_bytes: 3400,
    chunk_count: 9,
    tags: t([1]),
    created_at: "2026-01-17T10:15:00Z",
    updated_at: "2026-01-17T10:15:00Z",
  },
  {
    ...base,
    id: 19,
    filename: "samsung-mail.md",
    title: "Samsung Mail",
    description:
      "Android WebView rendering, dark mode behavior, and CSS support gaps",
    domain: "client_quirks",
    file_size_bytes: 3100,
    chunk_count: 8,
    tags: t([5]),
    created_at: "2026-01-17T10:20:00Z",
    updated_at: "2026-01-17T10:20:00Z",
  },
  {
    ...base,
    id: 20,
    filename: "outlook-web.md",
    title: "Outlook Web (Office 365)",
    description:
      "Forced colors mode, CSS limitations, and differences from desktop Outlook",
    domain: "client_quirks",
    file_size_bytes: 4200,
    chunk_count: 11,
    tags: t([8, 1]),
    created_at: "2026-01-17T10:25:00Z",
    updated_at: "2026-01-17T10:25:00Z",
  },
];

// ── Document Content (sample chunks for a few documents) ──

export const DEMO_KNOWLEDGE_CONTENT: Record<number, KnowledgeDocumentContent> =
  {
    1: {
      document_id: 1,
      filename: "layout-properties.md",
      title: "CSS Layout Properties",
      total_chunks: 12,
      chunks: [
        {
          chunk_index: 0,
          content:
            "# CSS Layout Properties in Email\n\nEmail clients have varying support for CSS layout properties. This document covers flexbox, grid, display, float, and position across all major email clients.",
        },
        {
          chunk_index: 1,
          content:
            "## Flexbox Support\n\nThe `display: flex` property is supported in Apple Mail, Samsung Mail, and most mobile clients. However, it is NOT supported in Gmail (web or app), Outlook (Windows), or Yahoo Mail. Always provide a table-based fallback when using flexbox.",
        },
        {
          chunk_index: 2,
          content:
            "## CSS Grid\n\n`display: grid` has even less support than flexbox in email. Only Apple Mail and a few niche clients support it. Do not rely on CSS Grid for email layouts. Use nested tables instead.",
        },
        {
          chunk_index: 3,
          content:
            "## Display Property\n\n`display: block`, `display: inline`, and `display: inline-block` are widely supported. `display: none` works everywhere except some older Outlook versions where `mso-hide: all` may be needed.",
        },
        {
          chunk_index: 4,
          content:
            "## Float\n\n`float: left` and `float: right` work in most clients except Outlook for Windows. Use `align` attributes on tables/images as a fallback. Floats can cause unpredictable reflow in some mobile clients.",
        },
      ],
    },
    8: {
      document_id: 8,
      filename: "dark-mode-css.md",
      title: "Dark Mode CSS",
      total_chunks: 15,
      chunks: [
        {
          chunk_index: 0,
          content:
            "# Dark Mode in Email\n\nDark mode support varies significantly across email clients. This guide covers the three main approaches: color-scheme meta tag, @media (prefers-color-scheme), and Outlook-specific overrides.",
        },
        {
          chunk_index: 1,
          content:
            '## The color-scheme Meta Tag\n\nAdd `<meta name="color-scheme" content="light dark">` and the CSS property `color-scheme: light dark` to signal dark mode support. Apple Mail, iOS Mail, and some Android clients respect this.',
        },
        {
          chunk_index: 2,
          content:
            "## @media (prefers-color-scheme: dark)\n\nThe most reliable approach for Apple Mail and iOS. Define dark-specific overrides inside this media query. Gmail and Outlook ignore this entirely.",
        },
        {
          chunk_index: 3,
          content:
            "## Outlook Dark Mode Overrides\n\nOutlook uses `data-ogsc` and `data-ogsb` attributes to force dark mode. Use `[data-ogsc]` selectors to override Outlook's auto-color remapping. The `!important` flag is usually needed.",
        },
      ],
    },
    15: {
      document_id: 15,
      filename: "outlook-windows.md",
      title: "Outlook on Windows",
      total_chunks: 18,
      chunks: [
        {
          chunk_index: 0,
          content:
            "# Outlook on Windows Rendering Guide\n\nOutlook 2007-2021+ on Windows uses the Microsoft Word HTML rendering engine, which has severe CSS limitations. This is the most challenging email client to support.",
        },
        {
          chunk_index: 1,
          content:
            "## MSO Conditional Comments\n\nUse `<!--[if mso]>` and `<!--[if !mso]><!-->` to serve Outlook-specific or non-Outlook code. This is the primary technique for providing fallbacks for Outlook's rendering limitations.",
        },
        {
          chunk_index: 2,
          content:
            "## VML Backgrounds\n\nOutlook doesn't support CSS `background-image`. Use VML (Vector Markup Language) with `v:rect` and `v:fill` to create background images. The `v:` namespace must be declared in the HTML tag.",
        },
        {
          chunk_index: 3,
          content:
            "## Table Rendering\n\nOutlook requires explicit widths on tables and cells. Percentage widths sometimes fail — use fixed pixel widths. Nested tables must have `border-collapse: collapse` and `cellpadding=\"0\" cellspacing=\"0\"`.",
        },
      ],
    },
    9: {
      document_id: 9,
      filename: "table-based-layout.md",
      title: "Table-Based Layout",
      total_chunks: 16,
      chunks: [
        {
          chunk_index: 0,
          content:
            "# Table-Based Email Layout\n\nDespite CSS advances, table-based layouts remain the most reliable approach for cross-client email compatibility. This guide covers essential patterns.",
        },
        {
          chunk_index: 1,
          content:
            '## The Outer Container Table\n\nStart with a full-width wrapper table: `<table role="presentation" width="100%" cellpadding="0" cellspacing="0">`. This provides the background color and centers the content table.',
        },
        {
          chunk_index: 2,
          content:
            "## Content Width\n\nKeep content tables between 580-640px wide. This ensures readability on desktop while leaving room for email client chrome. Use `max-width` for fluid hybrid layouts.",
        },
      ],
    },
    13: {
      document_id: 13,
      filename: "accessibility.md",
      title: "Email Accessibility",
      total_chunks: 13,
      chunks: [
        {
          chunk_index: 0,
          content:
            "# Email Accessibility Guide\n\nAccessible emails ensure all subscribers, including those using assistive technology, can read and interact with your content. Follow WCAG 2.1 Level AA guidelines.",
        },
        {
          chunk_index: 1,
          content:
            '## Language Attribute\n\nAlways set `<html lang="en">` (or appropriate language code). Screen readers use this to select the correct pronunciation engine.',
        },
        {
          chunk_index: 2,
          content:
            "## Image Alt Text\n\nEvery `<img>` must have an `alt` attribute. Decorative images use `alt=\"\"`. Informational images should have descriptive alt text under 125 characters. Avoid \"image of\" or \"picture of\" prefixes.",
        },
      ],
    },
  };
