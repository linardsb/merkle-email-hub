# Eval Human Labeling Guide

## Overview

After running the eval pipeline (`make eval-run` + `make eval-judge` + `make eval-labels`),
you'll have human label template files in `traces/`:

- `traces/scaffolder_human_labels.jsonl`
- `traces/dark_mode_human_labels.jsonl`
- `traces/content_human_labels.jsonl`

Each file contains one JSON object per line. Your job is to fill in the `human_pass` field.

## Label Format

Each line looks like:
```json
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "brief_fidelity", "judge_pass": true, "human_pass": null, "notes": ""}
```

**Your task:** Change `"human_pass": null` to `"human_pass": true` or `"human_pass": false`.

## How to Label

### Step 1: Open the traces file
Read the agent's trace file (e.g., `traces/scaffolder_traces.jsonl`) to see what the agent produced.
Each trace has an `output.html` field — this is what you're evaluating.

### Step 2: For each criterion, evaluate the output

**Judge criteria** (prefilled with judge's verdict in `judge_pass`):
- Read the criterion name and description
- Look at the agent's HTML output
- Decide: does this output PASS or FAIL for this criterion?
- Set `human_pass` to `true` or `false`
- Optionally add notes explaining your reasoning

**QA check criteria** (10 checks, `judge_pass` is null):
- These compare QA gate results to your judgment
- Look at the HTML and decide if each QA check SHOULD pass
- The QA gate's actual result is in the trace's `qa_results` field

### Step 3: Save the file

Keep it as valid JSONL (one JSON object per line, no trailing commas).

## Criteria Reference

### Scaffolder (5 judge criteria)
| Criterion | Pass if... |
|-----------|-----------|
| `brief_fidelity` | HTML implements all sections/elements requested in the brief |
| `email_layout` | Uses table-based layout, max-width 600px, cellpadding=0 |
| `mso_conditionals` | Has `<!--[if mso]>` blocks where needed (widths, VML) |
| `table_structure` | Tables are properly nested, no broken nesting |
| `code_quality` | Clean indentation, no redundant wrappers, semantic where possible |

### Dark Mode (5 judge criteria)
| Criterion | Pass if... |
|-----------|-----------|
| `color_coherence` | Dark colors are actually dark (not inverted to light) |
| `html_preservation` | No elements removed, layout structure identical to input |
| `outlook_selectors` | `[data-ogsc]`/`[data-ogsb]` selectors for all color overrides |
| `media_query` | `@media (prefers-color-scheme: dark)` block present and correct |
| `meta_tags` | `<meta name="color-scheme">` and `<meta name="supported-color-schemes">` present |

### Content (5 judge criteria)
| Criterion | Pass if... |
|-----------|-----------|
| `copy_quality` | Compelling, clear, scannable copy |
| `tone_match` | Matches the requested tone (formal, casual, urgent, etc.) |
| `spam_avoidance` | No ALL CAPS, excessive punctuation, or spam trigger phrases |
| `length_appropriate` | Meets length constraints for the operation type |
| `grammar` | No grammar or spelling errors |

### QA Gate Checks (10 criteria for all agents)
| Check | Pass if... |
|-------|-----------|
| `html_validation` | Valid DOCTYPE, html/head/body structure |
| `css_support` | No CSS properties with poor email client support |
| `file_size` | HTML < 102KB (Gmail clipping threshold) |
| `link_validation` | All links use HTTPS, valid protocols |
| `spam_score` | No common spam trigger words |
| `dark_mode` | color-scheme meta, prefers-color-scheme media query |
| `accessibility` | lang attribute, alt text on images, table roles |
| `fallback` | MSO conditional comments present |
| `image_optimization` | Images have explicit width/height, valid formats |
| `brand_compliance` | Passes brand rules (placeholder — usually passes) |

## Target Labels Per Agent

Aim for **20 labeled outputs per agent** (minimum for calibration).
The scaffolder has 12 traces, dark mode 10, content 14 — label all of them.

Each trace produces ~15 label rows (5 judge + 10 QA = 15 per trace).
Total labeling effort: ~540 rows across all 3 agents.

## Calibration Targets

After labeling, run `make eval-calibrate` and `make eval-qa-calibrate`.

- **Judge calibration:** TPR >= 0.85, TNR >= 0.80 per criterion
- **QA calibration:** Agreement rate >= 75% per check

If targets aren't met, iterate on judge prompts or QA check thresholds.
