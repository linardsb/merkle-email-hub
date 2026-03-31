"""Ingest real component HTML files as eval traces for HTML-evaluating agents.

Creates trace JSONL entries from email-templates/components/*.html for agents
that evaluate HTML quality: scaffolder, dark_mode, accessibility, outlook_fixer,
personalisation. Skips: content (text ops), code_reviewer (review quality),
knowledge (Q&A), innovation (deferred to separate phase).

Usage:
    python scripts/ingest-real-components.py \
        --components-dir email-templates/components \
        --output-dir traces \
        --manifest app/components/data/component_manifest.yaml
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Agents that evaluate HTML output directly
HTML_AGENTS = ["scaffolder", "dark_mode", "accessibility", "outlook_fixer", "personalisation"]

TIMESTAMP = datetime.now(tz=UTC).isoformat()

# Training HTML files with Figma design context (from synthetic_data_scaffolder.py cases 23-25)
TRAINING_HTML_CASES: list[dict[str, Any]] = [
    {
        "slug": "starbucks-pumpkin-spice",
        "file": "starbucks-pumpkin-spice.html",
        "id": "train-starbucks",
        "brief": (
            "Starbucks seasonal promotional email: Pumpkin Now, Peppermint On The Way. "
            "9 sections: full-width hero image, centered heading (40px, #1e3932 on #F2F0EB), "
            "italic body paragraph, VML pill CTA button (#1e3932, 25px radius), "
            "two-column holiday countdown, four-column icon navigation bar, "
            "social icons row, legal footer, Starbucks Rewards logo."
        ),
        "design_context": {
            "figma_url": "https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1424",
            "node_id": "2833-1424",
            "file_id": "VUlWjZGAEVZr3mK1EawsYR",
            "design_tokens": {
                "colors": {
                    "background": "#F2F0EB",
                    "primary_text": "#1e3932",
                    "cta_fill": "#1e3932",
                    "holiday_red": "#AA1733",
                    "nav_green": "#296042",
                },
                "fonts": {"heading": "SoDo Sans", "body": "SoDo Sans"},
                "font_sizes": {"heading": "40px", "body": "16px", "cta": "16px"},
                "spacing": {},
            },
            "section_mapping": [
                {
                    "section_index": 0,
                    "component_slug": "full-width-image",
                    "figma_frame_name": "Hero Image",
                },
                {"section_index": 1, "component_slug": "heading", "figma_frame_name": "Heading"},
                {
                    "section_index": 2,
                    "component_slug": "paragraph",
                    "figma_frame_name": "Body Text",
                },
                {
                    "section_index": 3,
                    "component_slug": "button-filled",
                    "figma_frame_name": "CTA Button",
                },
                {
                    "section_index": 4,
                    "component_slug": "column-layout-2",
                    "figma_frame_name": "Holiday Countdown",
                },
                {
                    "section_index": 5,
                    "component_slug": "column-layout-4",
                    "figma_frame_name": "Nav Bar",
                },
                {
                    "section_index": 6,
                    "component_slug": "footer-social",
                    "figma_frame_name": "Social Icons",
                },
                {
                    "section_index": 7,
                    "component_slug": "footer",
                    "figma_frame_name": "Legal Footer",
                },
                {"section_index": 8, "component_slug": "image", "figma_frame_name": "Rewards Logo"},
            ],
        },
        "expected_challenges": [
            "color_fidelity",
            "font_override",
            "section_mapping",
            "VML bulletproof button",
        ],
    },
    {
        "slug": "mammut-duvet-day",
        "file": "mammut-duvet-day.html",
        "id": "train-mammut",
        "brief": (
            "Mammut outdoor brand email: Grab A Duvet Day. 18 sections: "
            "hero image, heading (#E85D26 orange bg, white text, 32px, uppercase), "
            "body paragraph, ghost CTA button (white border on orange, VML, sharp corners), "
            "product images x 2, product headings, product CTAs, "
            "vertical navigation bar, three-column social icons, simple footer."
        ),
        "design_context": {
            "figma_url": "https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1135",
            "node_id": "2833-1135",
            "file_id": "VUlWjZGAEVZr3mK1EawsYR",
            "design_tokens": {
                "colors": {
                    "primary_orange": "#E85D26",
                    "heading_text": "#ffffff",
                    "body_text": "#ffffff",
                    "product_heading": "#1A1A1A",
                },
                "fonts": {"heading": "system-ui", "body": "system-ui"},
                "font_sizes": {"heading": "32px", "body": "14px", "nav_link": "16px"},
                "spacing": {},
            },
            "section_mapping": [
                {
                    "section_index": 0,
                    "component_slug": "full-width-image",
                    "figma_frame_name": "Hero Image",
                },
                {"section_index": 1, "component_slug": "heading", "figma_frame_name": "Heading"},
                {
                    "section_index": 2,
                    "component_slug": "paragraph",
                    "figma_frame_name": "Body Text",
                },
                {
                    "section_index": 3,
                    "component_slug": "button-ghost",
                    "figma_frame_name": "Ghost CTA",
                },
                {
                    "section_index": 12,
                    "component_slug": "navigation-bar",
                    "figma_frame_name": "Vertical Nav",
                },
                {"section_index": 14, "component_slug": "footer", "figma_frame_name": "Footer"},
            ],
        },
        "expected_challenges": ["color_fidelity", "18_section_structure", "class_based_dark_mode"],
    },
    {
        "slug": "maap-kask",
        "file": "maap-kask.html",
        "id": "train-maap",
        "brief": (
            "MAAP x KASK cycling brand collaboration email. 13 sections: "
            "full-width hero image, subtitle heading (12px #555555), "
            "main heading (36px #101828, 800 weight), body paragraph, "
            "ghost pill CTA button (25px radius), two-column product images, "
            "divider, vertical navigation bar, store locator pill button grid, "
            "three-column feature icons on #f7f7f7, dark footer (#000000 bg)."
        ),
        "design_context": {
            "figma_url": "https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1623",
            "node_id": "2833-1623",
            "file_id": "VUlWjZGAEVZr3mK1EawsYR",
            "design_tokens": {
                "colors": {
                    "heading_text": "#101828",
                    "body_text": "#555555",
                    "button_border": "#222222",
                    "divider": "#e0e0e0",
                    "feature_bg": "#f7f7f7",
                    "footer_bg": "#000000",
                    "pill_bg": "#222222",
                },
                "fonts": {"heading": "system-ui", "body": "system-ui"},
                "font_sizes": {"subtitle": "12px", "heading": "36px", "body": "16px"},
                "spacing": {},
            },
            "section_mapping": [
                {
                    "section_index": 0,
                    "component_slug": "full-width-image",
                    "figma_frame_name": "Hero Image",
                },
                {
                    "section_index": 2,
                    "component_slug": "heading",
                    "figma_frame_name": "Main Heading",
                },
                {
                    "section_index": 4,
                    "component_slug": "button-ghost",
                    "figma_frame_name": "Discover CTA",
                },
                {
                    "section_index": 5,
                    "component_slug": "column-layout-2",
                    "figma_frame_name": "Product Images",
                },
                {
                    "section_index": 7,
                    "component_slug": "navigation-bar",
                    "figma_frame_name": "Vertical Nav",
                },
                {
                    "section_index": 11,
                    "component_slug": "footer",
                    "figma_frame_name": "Dark Footer",
                },
            ],
        },
        "expected_challenges": [
            "color_fidelity",
            "monochrome_palette",
            "pill_button_grid_composite",
        ],
    },
]


def load_manifest(manifest_path: Path) -> dict[str, dict[str, str]]:
    """Load component manifest YAML, return {slug: metadata}."""
    data = yaml.safe_load(manifest_path.read_text())
    return {
        c["slug"]: {
            "name": c.get("name", c["slug"]),
            "description": c.get("description", ""),
            "category": c.get("category", "unknown"),
            "compatibility": c.get("compatibility", "unknown"),
        }
        for c in data.get("components", [])
    }


def build_trace(
    agent: str,
    slug: str,
    html: str,
    meta: dict[str, str],
) -> dict[str, Any]:
    """Build a trace dict for a given agent and component."""
    trace_id = f"real-{slug}"
    category = meta.get("category", "unknown")
    name = meta.get("name", slug)
    description = meta.get("description", "")

    base: dict[str, Any] = {
        "id": trace_id,
        "agent": agent,
        "expected_challenges": [],
        "elapsed_seconds": 0.0,
        "error": None,
        "timestamp": TIMESTAMP,
    }

    if agent == "scaffolder":
        base["dimensions"] = {
            "layout_complexity": "real_component",
            "content_type": category,
            "client_quirk": "real_component",
            "brief_quality": "n/a",
        }
        base["input"] = {"brief": f"Generate a {name} email component: {description}"}
        base["output"] = {
            "html": html,
            "qa_results": [],
            "qa_passed": True,
            "model": "real-component",
        }

    elif agent == "dark_mode":
        base["dimensions"] = {
            "input_html_complexity": "real_component",
            "color_scenario": category,
            "outlook_challenge": "real_component",
            "image_scenario": "real_component",
        }
        base["input"] = {
            "html_input": html,
            "html_length": len(html),
            "color_overrides": None,
            "preserve_colors": None,
        }
        base["output"] = {
            "html": html,
            "qa_results": [],
            "qa_passed": True,
            "model": "real-component",
        }

    elif agent == "accessibility":
        base["dimensions"] = {
            "violation_category": "real_component",
            "html_complexity": category,
            "image_scenario": "real_component",
            "severity": "real_component",
        }
        base["input"] = {"brief": f"Evaluate accessibility of {name} component"}
        base["output"] = {
            "html": html,
            "qa_results": [],
            "qa_passed": True,
            "model": "real-component",
        }

    elif agent == "outlook_fixer":
        base["dimensions"] = {
            "layout_complexity": "real_component",
            "rendering_issue_type": category,
            "vml_requirement": "real_component",
            "mso_version": "real_component",
        }
        base["input"] = {"html_input": html, "html_length": len(html)}
        base["output"] = {
            "html": html,
            "fixes_applied": [],
            "qa_results": [],
            "qa_passed": True,
            "model": "real-component",
        }

    elif agent == "personalisation":
        base["dimensions"] = {
            "platform": "braze",
            "complexity_level": "real_component",
            "variable_density": category,
            "requirement_type": "real_component",
        }
        base["input"] = {"html": html, "platform": "braze"}
        base["output"] = {
            "html": html,
            "qa_results": [],
            "qa_passed": True,
            "model": "real-component",
        }

    return base


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest real components as eval traces")
    parser.add_argument(
        "--components-dir",
        type=Path,
        default=Path("email-templates/components"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("traces"))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("app/components/data/component_manifest.yaml"),
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("traces/pre_real_components"),
        help="Directory to backup existing synthetic traces",
    )
    args = parser.parse_args()

    # Load manifest
    manifest = load_manifest(args.manifest)
    print(f"Loaded manifest: {len(manifest)} components")

    # Collect component HTML files (top-level only)
    html_files = sorted(args.components_dir.glob("*.html"))
    print(f"Found {len(html_files)} HTML files in {args.components_dir}")

    # Backup existing traces
    args.backup_dir.mkdir(parents=True, exist_ok=True)
    for agent in HTML_AGENTS:
        for suffix in ["_traces.jsonl", "_verdicts.jsonl", "_human_labels.jsonl"]:
            src = args.output_dir / f"{agent}{suffix}"
            if src.exists():
                dst = args.backup_dir / f"{agent}{suffix}"
                dst.write_text(src.read_text())
    print(f"Backed up existing traces to {args.backup_dir}")

    # Build traces per agent
    for agent in HTML_AGENTS:
        traces: list[dict[str, Any]] = []
        for html_file in html_files:
            slug = html_file.stem
            html = html_file.read_text()

            # Get metadata from manifest, fall back to slug-derived
            meta = manifest.get(
                slug,
                {
                    "name": slug.replace("-", " ").title(),
                    "description": "",
                    "category": "unknown",
                    "compatibility": "unknown",
                },
            )

            trace = build_trace(agent, slug, html, meta)
            traces.append(trace)

        # Write traces JSONL
        output_path = args.output_dir / f"{agent}_traces.jsonl"
        with Path.open(output_path, "w") as f:
            for trace in traces:
                f.write(json.dumps(trace) + "\n")

        print(f"  {agent}: {len(traces)} traces -> {output_path}")

    # Ingest training HTMLs (complete assembled emails with design context)
    training_dir = args.components_dir.parent / "training_HTML" / "for_converter_engine"
    training_count = 0
    if training_dir.exists():
        scaffolder_path = args.output_dir / "scaffolder_traces.jsonl"
        with Path.open(scaffolder_path, "a") as f:
            for case in TRAINING_HTML_CASES:
                html_file = training_dir / case["file"]
                if not html_file.exists():
                    print(f"  WARNING: training file not found: {html_file}")
                    continue
                html = html_file.read_text()
                trace: dict[str, Any] = {
                    "id": case["id"],
                    "agent": "scaffolder",
                    "dimensions": {
                        "layout_complexity": "assembled_email",
                        "content_type": "training_html",
                        "client_quirk": "real_component",
                        "brief_quality": "detailed_with_sections",
                        "design_fidelity": "full_figma_context",
                    },
                    "input": {"brief": case["brief"]},
                    "output": {
                        "html": html,
                        "qa_results": [],
                        "qa_passed": True,
                        "model": "real-training-html",
                    },
                    "design_context": case["design_context"],
                    "expected_challenges": case["expected_challenges"],
                    "elapsed_seconds": 0.0,
                    "error": None,
                    "timestamp": TIMESTAMP,
                }
                f.write(json.dumps(trace) + "\n")
                training_count += 1
        print(
            f"\n  + {training_count} training HTMLs with Figma design context -> scaffolder traces"
        )

    total = len(html_files) * len(HTML_AGENTS) + training_count
    print(
        f"\nTotal: {total} traces ({len(html_files)} components x {len(HTML_AGENTS)} agents + {training_count} training HTMLs)"
    )
    print("\nNext steps:")
    print("  1. Run judges: make eval-rejudge (or per-agent)")
    print("  2. Run labels: make eval-labels")
    print("  3. Generate review data: python scripts/generate-review-data.py")


if __name__ == "__main__":
    main()
