<!-- L4 source: docs/SKILL_email-dark-mode-dom-reference.md -->
# Meta Tag Injection — Deterministic Safety Net

## Overview

A post-generation validator automatically injects missing dark mode meta tags.
You do NOT need to worry about forgetting them — the system catches omissions.
However, you SHOULD still include them in your output for best results.

## Required Meta Tags (Both Must Be Present)

1. `<meta name="color-scheme" content="light dark">` — Tells email clients
   this email supports both light and dark colour schemes
2. `<meta name="supported-color-schemes" content="light dark">` — Legacy
   compatibility tag for older Apple Mail versions

## Placement Rules

- Both tags MUST be in `<head>`, NOT in `<body>`
- Place them early in `<head>`, before `<style>` blocks
- Order: `color-scheme` first, then `supported-color-schemes`

## What the Injector Does

If your output is missing either tag, the deterministic injector will:
1. Parse the HTML with lxml to check tag presence
2. Insert missing tag(s) immediately before `</head>`
3. Log the injection for the handoff chain

## Common LLM Mistakes

| Mistake | Frequency | Injector Fixes? |
|---------|-----------|----------------|
| Omits both meta tags entirely | ~25% | Yes |
| Includes color-scheme but not supported-color-schemes | ~20% | Yes |
| Includes supported-color-schemes but not color-scheme | ~5% | Yes |
| Places meta tags in `<body>` instead of `<head>` | ~5% | No (parser detects but injector adds to `<head>`) |
| Wrong content value (e.g., "dark" instead of "light dark") | ~3% | No (tag present, content not validated by injector) |

## Best Practice

Always output both meta tags in `<head>`. The injector is a safety net,
not a substitute for correct generation.
