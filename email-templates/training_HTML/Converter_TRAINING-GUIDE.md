# Training Guide — Converter & Agent Learning Loop

How to feed new Figma designs, HTML emails, and screenshots into the system
so the converter and agents improve with every campaign run.

---

## Prerequisites

```bash
# Backend running
make dev

# Verify DB is up
uv run python -c "
import asyncio
from app.core.database import get_db_context
async def check():
    async with get_db_context() as db:
        await db.execute(__import__('sqlalchemy').text('SELECT 1'))
        print('DB OK')
asyncio.run(check())
"
```

For Figma operations you need a **Personal Access Token** (PAT):
- Go to Figma > Settings > Account > Personal Access Tokens
- Create a token with read access
- Export it: `export FIGMA_TOKEN=figd_xxxxxxxxxxxxx`

---

## Method 1: Train from Figma Design URL (Automatic Learning)

This is the **primary training path**. Every conversion through the API
automatically persists quality data to memory, insights, and traces.

### Step 1 — Get a JWT token

```bash
export ACCESS_TOKEN=$(curl -s -X POST http://localhost:8891/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}' | jq -r '.access_token')
```

### Step 2 — Create a Figma connection

```bash
curl -s -X POST http://localhost:8891/api/v1/design-sync/connections \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Email Designs",
    "provider": "figma",
    "file_url": "https://www.figma.com/design/YOUR_FILE_KEY/Your-File-Name",
    "access_token": "'$FIGMA_TOKEN'"
  }' | jq
```

Save the `id` from the response:

```bash
export CONNECTION_ID=8  # replace with actual ID
```

### Step 3 — Find the frame node ID

Browse the file structure to find the email frame you want to convert:

```bash
curl -s http://localhost:8891/api/v1/design-sync/connections/$CONNECTION_ID/file-structure?depth=2 \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.pages[].frames[] | {id, name}'
```

This lists all top-level frames with their node IDs (e.g., `"2833:1424"`).

### Step 4 — Create an import with a brief

```bash
IMPORT_RESPONSE=$(curl -s -X POST http://localhost:8891/api/v1/design-sync/imports \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": '$CONNECTION_ID',
    "brief": "Create a promotional campaign email with hero image, product showcase, CTA buttons, and branded footer.",
    "selected_node_ids": ["2833:1424"]
  }')

export IMPORT_ID=$(echo $IMPORT_RESPONSE | jq -r '.id')
echo "Import ID: $IMPORT_ID"
```

The `brief` tells the Scaffolder what kind of email to generate. Be descriptive —
mention the layout, sections, and purpose.

### Step 5 — Start the conversion

```bash
curl -s -X POST http://localhost:8891/api/v1/design-sync/imports/$IMPORT_ID/convert \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "run_qa": true,
    "output_mode": "structured",
    "output_format": "html"
  }' | jq '.status'
```

### Step 6 — Poll until complete

```bash
while true; do
  STATUS=$(curl -s http://localhost:8891/api/v1/design-sync/imports/$IMPORT_ID \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] && break
  sleep 3
done
```

### What happens automatically

When conversion completes, Phase 48 fires in the background:

1. **Memory entry** stored in PostgreSQL with quality warnings, match confidences,
   and design tokens — the Scaffolder reads this on every future conversion
2. **Insights** sent to the insight bus if any section had low match confidence
   (< 0.6) — the Scaffolder uses these to avoid repeating bad template choices
3. **JSONL trace** appended to `traces/converter_traces.jsonl` — used for
   regression detection

### Step 7 — Check what was learned

```bash
# View the latest trace
tail -1 traces/converter_traces.jsonl | jq '{
  trace_id, quality_score, avg_confidence,
  warnings: (.warnings | length),
  sections_count
}'

# Run regression check
make converter-regression
```

---

## Method 2: Train from HTML Email Files

Use this when you have finished HTML emails (from production, email galleries,
or competitors) that represent "good" output.

### Option A — Add as a snapshot case (recommended)

This registers the HTML as a regression test case so the converter is
continuously tested against it.

#### Step 1 — Extract the design data from Figma

```bash
python -m app.design_sync.diagnose.extract \
  --connection-id $CONNECTION_ID \
  --node-id 2833:1424 \
  --output-dir data/debug/NEW_CASE_ID
```

Or if you have a Figma URL but no connection:

```bash
FIGMA_TOKEN=figd_xxx python -m app.design_sync.diagnose.extract \
  --figma-url "https://www.figma.com/design/FILE_KEY/Name" \
  --node-id 2833:1424 \
  --output-dir data/debug/NEW_CASE_ID
```

This creates:
- `data/debug/NEW_CASE_ID/structure.json` — design tree
- `data/debug/NEW_CASE_ID/tokens.json` — colors, fonts, spacing
- `data/debug/NEW_CASE_ID/report.json` — diagnostic report

#### Step 2 — Place your reference HTML

Copy the "ideal" HTML output into the case directory:

```bash
cp my-email.html data/debug/NEW_CASE_ID/expected.html
```

Open it in a browser and verify it looks correct.

#### Step 3 — Register in the manifest

Edit `data/debug/manifest.yaml`:

```yaml
cases:
  # ... existing cases ...
  - id: "NEW_CASE_ID"
    name: "Your Email Name — brief description of sections"
    source: "Where this design came from"
    figma_node: "2833:1424"
    sections: 8       # how many sections the converter currently produces
    target_sections: 12  # how many the design actually has
    status: active
```

#### Step 4 — Run snapshot test to verify

```bash
make snapshot-test
```

If the test fails (expected — your HTML probably differs from converter output),
that's fine. The snapshot becomes a **convergence target** — as the converter
improves, it should get closer to your expected.html.

#### Step 5 — Backfill learning data

```bash
# Dry run first
python scripts/backfill-conversion-memories.py --dry-run

# Then write traces (always works, no API keys needed)
python scripts/backfill-conversion-memories.py --traces-only

# Or full backfill with memory entries (needs embedding provider)
python scripts/backfill-conversion-memories.py
```

### Option B — Upload via API

Use this for quick analysis without creating a permanent test case:

```bash
# Read the HTML file and POST it
HTML_CONTENT=$(cat my-email.html | jq -Rs .)

curl -s -X POST http://localhost:8891/api/v1/design-sync/import/html \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "html": '$HTML_CONTENT',
    "use_ai": true,
    "source_name": "training_email_001"
  }' | jq '{section_count, ai_sections_classified, warnings}'
```

This analyzes the HTML structure but does **not** automatically trigger learning.
Use Option A for permanent training data.

### Option C — Upload as reusable template

```bash
curl -s -X POST http://localhost:8891/api/v1/templates/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@my-email.html"
```

Then confirm:

```bash
curl -s -X POST http://localhost:8891/api/v1/templates/upload/$UPLOAD_ID/confirm \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

This stores the template for reuse by the Scaffolder but does not run it
through the learning loop.

---

## Method 3: Train from Screenshots (Diagnostic Comparison)

Screenshots are useful for visual fidelity comparison — comparing what the
Figma design looks like vs what the converter produced.

### Step 1 — Capture the Figma design screenshot

```bash
python -m app.design_sync.diagnose.extract \
  --connection-id $CONNECTION_ID \
  --node-id 2833:1424 \
  --output-dir data/debug/MY_CASE
```

This saves `data/debug/MY_CASE/design.png` (the Figma screenshot) and
`data/debug/MY_CASE/design_meta.json` (dimensions, scale).

To skip the screenshot (faster):

```bash
python -m app.design_sync.diagnose.extract \
  --connection-id $CONNECTION_ID \
  --node-id 2833:1424 \
  --no-image
```

### Step 2 — Generate the converter output

```bash
make snapshot-capture CASE=MY_CASE
```

This runs the converter and saves the HTML to
`data/debug/MY_CASE/output.html`.

### Step 3 — Visual comparison

Open both side by side:

```bash
open data/debug/MY_CASE/design.png
open data/debug/MY_CASE/output.html
```

### Step 4 — Run visual regression (if Playwright is installed)

```bash
make snapshot-visual
```

This renders the converter output in a headless browser and compares it
against the design screenshot using SSIM (structural similarity).

### Step 5 — Store as training data

If you're satisfied with the comparison, register it as a snapshot case
(see Method 2, Option A, Steps 3-5).

---

## Batch Training — Multiple Designs at Once

### From multiple Figma frames in the same file

```bash
# List all frames
curl -s http://localhost:8891/api/v1/design-sync/connections/$CONNECTION_ID/file-structure?depth=2 \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.pages[].frames[] | {id, name}'

# Convert each frame (repeat for each node ID)
for NODE_ID in "2833:1424" "2833:1623" "2833:1135"; do
  IMPORT_ID=$(curl -s -X POST http://localhost:8891/api/v1/design-sync/imports \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "connection_id": '$CONNECTION_ID',
      "brief": "Convert this email design to HTML",
      "selected_node_ids": ["'$NODE_ID'"]
    }' | jq -r '.id')

  curl -s -X POST http://localhost:8891/api/v1/design-sync/imports/$IMPORT_ID/convert \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"run_qa": true}' > /dev/null

  echo "Started conversion for node $NODE_ID (import $IMPORT_ID)"
  sleep 2  # respect rate limit (3/minute)
done
```

### From a folder of HTML files

```bash
# Place HTML files in email-templates/training_HTML/
# Then extract and register each as a snapshot case:

for HTML_FILE in email-templates/training_HTML/*.html; do
  CASE_ID=$(basename "$HTML_FILE" .html)
  mkdir -p "data/debug/$CASE_ID"
  cp "$HTML_FILE" "data/debug/$CASE_ID/expected.html"
  echo "Registered case: $CASE_ID"
done

# Note: These cases won't have structure.json/tokens.json
# They serve as reference targets only (no converter comparison)
```

---

## Monitoring Training Progress

### Check quality trends

```bash
uv run python -c "
import json
with open('traces/converter_traces.jsonl') as f:
    for line in f:
        t = json.loads(line)
        print(f'{t[\"trace_id\"]:40s}  score={t[\"quality_score\"]:.3f}  '
              f'conf={t[\"avg_confidence\"]:.2f}  '
              f'warnings={len(t[\"warnings\"]):2d}  '
              f'sections={t[\"sections_count\"]}')
"
```

### Check regression baseline

```bash
make converter-regression
```

Sample output:
```
Converter regression check: PASSED
  avg_quality_score: 0.7585 (baseline: 0.7585)
  avg_confidence: 0.9948 (baseline: 0.9948)
  warning_rate: 1.0385 (baseline: 1.0385)
  error_rate: 0.0000 (baseline: 0.0000)
  low_confidence_section_rate: 0.0000 (baseline: 0.0000)
```

If quality drops more than 5% from baseline, the check fails.

### Update baseline after improvements

```bash
python -m app.design_sync.converter_regression --update-baseline
```

### View stored memories (what the Scaffolder sees)

```bash
# Query memories via API
curl -s -X POST http://localhost:8891/memory/search \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "conversion quality",
    "agent_type": "design_sync",
    "limit": 10
  }' | jq '.[] | {content: .content[:100], created_at}'
```

---

## Quick Reference — All Commands

| Task | Command |
|------|---------|
| Start backend | `make dev` |
| Extract Figma design data | `python -m app.design_sync.diagnose.extract --connection-id N --node-id X` |
| List Figma frames | `python -m app.design_sync.diagnose.extract --connection-id N --list-frames` |
| Run converter on snapshot case | `make snapshot-capture CASE=N` |
| Run snapshot regression tests | `make snapshot-test` |
| Run visual regression | `make snapshot-visual` |
| Backfill learning (dry run) | `python scripts/backfill-conversion-memories.py --dry-run` |
| Backfill learning (traces only) | `python scripts/backfill-conversion-memories.py --traces-only` |
| Backfill learning (full) | `python scripts/backfill-conversion-memories.py` |
| Check quality regression | `make converter-regression` |
| Update regression baseline | `python -m app.design_sync.converter_regression --update-baseline` |
| View quality trends | `cat traces/converter_traces.jsonl \| jq '{trace_id, quality_score}'` |

---

## How the Learning Loop Works

```
                    ┌──────────────────────┐
                    │   Figma Design URL   │
                    │   or HTML Upload     │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │   Converter Pipeline │
                    │   (layout analysis,  │
                    │    component match,  │
                    │    HTML generation)  │
                    └──────────┬───────────┘
                               ▼
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
     ┌────────────┐   ┌──────────────┐   ┌───────────┐
     │  Memory    │   │  Insight Bus │   │   JSONL   │
     │  (Postgres)│   │  (Scaffolder)│   │  Traces   │
     └─────┬──────┘   └──────┬───────┘   └─────┬─────┘
           │                 │                  │
           ▼                 ▼                  ▼
     ┌──────────┐     ┌───────────┐      ┌───────────┐
     │Scaffolder│     │ Template  │      │Regression │
     │ recalls  │     │ selection │      │ detection │
     │ history  │     │ adjusted  │      │ baseline  │
     └──────────┘     └───────────┘      └───────────┘
           │                 │
           └────────┬────────┘
                    ▼
           Next conversion is
           better informed
```

Each conversion makes the next one smarter. The Scaffolder sees past quality
issues and adjusts its template selection. The regression detector catches
quality drops early. The traces provide a permanent audit trail.
