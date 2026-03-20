# Design Import Pipeline

Imports a design from Figma, builds an email from it via the AI blueprint engine, runs QA checks, and gates on admin approval.

**Flow ID:** `design-import-pipeline`
**Trigger:** Manual
**Namespace:** `merkle-email-hub`

## When to Use

- A designer has finalized an email design in Figma and you need to convert it to production HTML
- You want automated QA on the design-to-code conversion before it goes live
- Bridging the design-to-development handoff with quality gates

## Pipeline Steps

```
build (AI Blueprint from Design)
  │  retries: 3 × 30s
  ▼
qa (QA Checks)
  ▼
approval (Admin Gate)
```

1. **build** (`hub.blueprint_run`) — Runs the AI blueprint engine with the imported design context to generate email HTML. Retries up to 3 times.
2. **qa** (`hub.qa_check`) — Runs the full QA suite against the generated HTML to catch rendering issues, accessibility problems, and brand compliance violations.
3. **approval** (`hub.approval_gate`) — Pauses and waits for admin approval before the template is considered ready.

Note: This pipeline does **not** include an ESP push step — it stops at approval. The approved template can then be used in a campaign or newsletter workflow.

## Inputs

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `figma_file_ref` | string | Yes | — | Figma file reference (file key or URL) |
| `project_id` | integer | Yes | — | Project ID for design system context |

## Example JSON Input

```json
{
  "figma_file_ref": "abc123XYZ",
  "project_id": 42
}
```

With a full Figma URL (the system extracts the file key):

```json
{
  "figma_file_ref": "https://www.figma.com/file/abc123XYZ/Email-Campaign-Q3",
  "project_id": 42
}
```

## Outputs

| Output | Source | Description |
|--------|--------|-------------|
| `outputs.build.html` | build step | Generated email HTML from the Figma design |
| `outputs.build.run_id` | build step | Blueprint run ID |
| QA results | qa step | Pass/fail per check |
| Approval record | approval step | Who approved and when |

## Where to Find Input Values

- **`figma_file_ref`** — Open the design in Figma, copy the URL. The file key is the alphanumeric string after `/file/` in the URL. You can also find connected designs in **Ecosystem > Penpot/Figma**
- **`project_id`** — Found in the URL when viewing a project, or via `GET /api/v1/projects/`

## Notes

- This pipeline focuses on design-to-code conversion and validation — it does not deploy
- To deploy the approved template, trigger the **Multilingual Campaign** or **Weekly Newsletter** workflow with the resulting template
- The build step uses a generic brief ("Build email from imported design") — the design file itself provides the visual context to the AI
