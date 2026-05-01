# Feature comparison matrix

**Caveat up front:** This compares email-hub's *documented architecture* against competitors' *marketing claims*. Both are biased toward optimism. Take the wins below as "documented capability vs advertised capability" — not "proven in customer production." Email-hub's "99% fidelity" claim is from internal snapshot tests, not customer telemetry.

---

## High-level feature scoreboard

Legend: ✅ shipped & advertised, 🟡 partial, ❌ absent, ⭐️ best-in-class claim

| Capability | email-hub | Stensul | Knak | Dyspatch | Email Love | Composa | Beefree | Klaviyo | SFMC Einstein | Mailmodo |
|---|---|---|---|---|---|---|---|---|---|---|
| **Multi-agent LLM pipeline** | ⭐️ 9 agents + DAG | 🟡 feature suite | 🟡 feature suite | 🟡 Scribe AI | 🟡 AI Studio | 🟡 single-pass | 🟡 BEE AI | ✅ Composer | ✅ Einstein | ✅ |
| **VLM visual verification loop** | ⭐️ iterative | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Calibrated eval system (TPR/TNR)** | ⭐️ research-grade | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Adversarial / synthetic QA** | ⭐️ 7-attack suite | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **14 specialised QA checks bundled** | ⭐️ | ❌ | ❌ | 🟡 Litmus integrated | ❌ | ❌ | 🟡 brand controls | 🟡 | 🟡 | ❌ |
| **Brand pipeline / token replacement** | ⭐️ Euclidean RGB nearest-match | ✅ guardrails | ✅ guardrails | ✅ | ✅ design system sync | ✅ design system sync | ✅ | ✅ brand voice | ✅ 10 personalities | 🟡 |
| **Per-section structural fidelity** | ⭐️ sibling groups + content roles | ❌ | 🟡 Figma plugin | 🟡 | 🟡 MJML conversion | ✅ structural bridge | ❌ | ❌ | ❌ | ❌ |
| **Tree compiler (deterministic, LLM-free)** | ⭐️ EmailTree → HTML | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Pipeline contracts / hooks** | ⭐️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Prompt injection guard + PII redaction** | ⭐️ | ❌ advertised | ❌ advertised | ❌ advertised | ❌ advertised | ❌ advertised | ❌ advertised | ❌ advertised | ✅ via Salesforce | ❌ advertised |
| **AMP for Email** | ❌ | ❌ | ❌ | ⭐️ pre-coded blocks | ❌ | ❌ | ❌ | ❌ | ❌ | ⭐️ specialty |
| **Translation / localisation** | ✅ Tolgee | 🟡 | 🟡 | ⭐️ 300+ locales | 🟡 Excel | ❌ | ❌ | ✅ | ✅ | 🟡 |
| **Drag-and-drop builder polish** | 🟡 ships, UX maturity unverified | ⭐️ | ⭐️ | ✅ | ✅ Figma-based | ✅ | ⭐️ | ✅ | ✅ | ✅ |
| **Approvals workflow** | ✅ | ⭐️ | ⭐️ | ✅ | ❌ | 🟡 | ✅ | ❌ | ✅ | ❌ |
| **CRDT real-time collab** | ⭐️ Yjs + Hypothesis | ✅ collab | ✅ collab | ✅ commenting | ❌ | 🟡 | ✅ | ❌ | ❌ | ❌ |
| **MCP server (external)** | ❌ | ❌ | ⭐️ Apr 2026 | ❌ | ❌ | ❌ | ❌ | ❌ | 🟡 Agentforce | ❌ |
| _(also Customer.io shipped MCP April 2026 — not in this column but noted)_ | | | | | | | | | | |
| **ESP integrations breadth** | 🟡 9 connectors | ⭐️ 100+ | ⭐️ 8 enterprise + API | ✅ 11+ | ✅ 13 | 🟡 6 | ✅ 10+ | n/a (is ESP) | n/a (is ESP) | 🟡 40+ |
| **BYOL / customer LLM keys** | ✅ via adapters (not packaged) | 🟡 "coming soon" Azure/Bedrock/Gemini | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Cron / scheduling** | ⭐️ leader-elected | 🟡 enterprise | 🟡 enterprise | 🟡 | ❌ | ❌ | ❌ | ✅ flows | ✅ journeys | ✅ |
| **Plugin / SDK extensibility** | ✅ plugin system | ❌ | 🟡 API | 🟡 API | ❌ | ❌ | ⭐️ SDK in 1,000+ apps | ❌ | 🟡 | ❌ |
| **Public template library / inspiration** | ❌ (14 golden refs internal) | ❌ | 🟡 | 🟡 | ⭐️ 6,000-brand gallery | ❌ | ⭐️ 2,000+ | ✅ | ✅ | 🟡 |
| **Customer logos / case studies** | ❌ | ⭐️ BlackRock, Cisco, Siemens | ⭐️ OpenAI, Meta, Google | ✅ | 🟡 | ❌ pre-launch | ⭐️ Netflix, L'Oreal, UNICEF | ⭐️ 193k brands | ⭐️ enterprise | ✅ foundit, bigbasket |
| **Public pricing** | ❌ | ❌ enterprise sales | ❌ enterprise sales | ⭐️ $149/$499/custom | ⭐️ $19/$35/custom | ❌ waitlist | ⭐️ tiers visible | ⭐️ tiers visible | n/a license-bundled | 🟡 |

---

## Where email-hub is genuinely ahead

These are differentiators *no competitor advertises matching*. They're the moat.

### 1. Multi-agent DAG pipeline with adversarial evaluator

email-hub: 9 specialised agents (Scaffolder, Dark Mode, Content, Outlook Fixer, Accessibility, Personalisation, Code Reviewer, Knowledge, Innovation) + visual_qa + import_annotator + skills agents. Kahn's toposort ensures correct execution order. Async per-level execution via `asyncio.gather`. Contracts validate per-node output. Hooks system at 7 injection points. **Evaluator agent enforces different-provider review** (e.g. OpenAI generates → Anthropic evaluates) — adversarial quality control most teams haven't even discussed.

Competitors: feature-suites of AI capabilities (Stensul's Email Generator, Knak AI co-pilot, Dyspatch's Scribe), not orchestrated multi-agent pipelines with quality gates.

**Why it matters for sales:** "Two LLMs from different providers must agree before output ships" is a story enterprise risk/compliance teams understand.

### 2. VLM visual verification loop

email-hub: Render → ODiff pre-filter → VLM section-by-section comparison → structured correction extraction → deterministic CSS/style/content correction applicator → re-render → measure fidelity → iterate. Convergence detection. Regression revert. ~99% claimed fidelity (Phase 47).

Competitors: zero advertise this. MigmaAI claims 95% accuracy but as a one-shot conversion. Composa says "structural bridge" but doesn't claim per-section verification.

**Why it matters for sales:** Demo-able. You can record a 60-second video of a Figma file → low-fidelity first render → verification loop fixing 12 specific issues → 99% match. **That's the marketing artifact you don't have yet.**

### 3. Calibrated evaluation system

email-hub: TPR/TNR-calibrated binary judges, 540 human-labelled rows, golden cases (deterministic CI test), production-trace sampling, 7-attack adversarial suite (prompt injection, jailbreak, etc.), correction-impact A/B (judge with vs. without corrections), meta-evaluation of QA checks themselves (precision/recall/F1 on the checkers).

Competitors: zero advertise this. Most ship LLM features without calibration discipline.

**Why it matters for sales:** This is the only path to selling AI-generated email to regulated industries (financial services, healthcare). "Our judges have measured TPR/TNR; here are the calibration curves" is the kind of thing a CISO can sign off on.

### 4. 14 specialised QA checks bundled

email-hub: BIMI verification, Gmail intelligence, Outlook-specific analyzer, deliverability with ISP profiles (Gmail/Microsoft/Yahoo), dark-mode parser, MSO parser, accessibility, brand compliance, image optimization, link validation, liquid syntax, personalisation syntax, file size, html_validation. Plus repair pipeline for auto-fix.

Competitors: Litmus (~$500/mo) is the dedicated QA platform. Stensul/Knak/Dyspatch do not advertise this depth.

**Why it matters for sales:** "Litmus + Stensul" is what enterprise teams currently pay for. Email-hub bundles both. That's a packaging advantage.

### 5. Tree compiler (deterministic LLM-free assembly)

email-hub: EmailTree Pydantic schema (Phase 48.6) + TreeCompiler (Phase 48.8) deterministically compile a structured tree to HTML with no LLM in the compile path. Slot-filling caching by MD5 keys. Inline CSS manipulation via lxml.

Competitors: most competitors LLM all the way through, which makes their output non-deterministic and uncacheable.

**Why it matters for sales:** Cost story. "We use LLM only where judgment is needed; assembly is deterministic" → 5–10× cheaper unit economics than always-LLM competitors.

### 6. Per-section structural fidelity

email-hub: sibling repeating-group detection (Phase 49.1), content-role inference (Phase 49.3), child content groups (Phase 49.5), token scoping per-frame (Phase 49.6), button stroke/icon extraction (Phase 49.7), tree bridge (Phase 49.8).

Competitors: Email Love and Composa convert frames; this is more semantic.

**Why it matters for sales:** Higher fidelity = less manual tweaking after generation = the actual product promise of "Figma to email" tools.

### 7. Brand pipeline with deterministic palette/font enforcement

email-hub: LAYER 11 in BlueprintEngine, Euclidean RGB nearest-match for off-palette colors, role-based slot locking, deterministic palette/font replacement during repair stage 8.

Competitors: guardrails (Stensul/Knak), brand voice (Klaviyo/SFMC), but the deterministic post-generation enforcement layer is more rigorous.

### 8. Security posture

email-hub: per-agent sanitization profiles (10 nh3 allowlists), prompt-injection guard (5 pattern categories, 3 modes), PII redaction in logs/traces (5 regex patterns), secured at every system boundary.

Competitors: not advertised at this depth. Salesforce/Adobe inherit enterprise security from the platform; standalone tools don't.

### 9. Operational maturity

email-hub: Cron scheduler with Redis leader election + croniter, debouncer with token-based distributed debouncing, credential pool with rotation + cooldowns + provider failover, notification router (Slack/Teams/Email), plugin system with sample ESP connector, observability stack (Grafana + Loki + Promtail).

Competitors: this is buried in enterprise plans elsewhere. Knak/Stensul don't advertise scheduler/credential-rotation features explicitly.

---

## Where email-hub is at parity

These are real but won't differentiate.

- **ESP integrations**: 9 connectors (Braze, SFMC, Adobe, HubSpot, Iterable, Klaviyo, Mailchimp, Brevo, ActiveCampaign). Email Love has 13. Stensul has 100+ via SFMC/Adobe partner ecosystem. You're competitive but not best-in-class.
- **Drag-and-drop builder**: present, but UX maturity vs. Beefree/Stensul/Knak's years of polish is unverified.
- **Approvals workflow**: present and serviceable; competitors have it too.
- **Translation/TMS**: Tolgee integration is good. Dyspatch advertises 300+ locales as flagship; you're competitive but they own the narrative.
- **Real-time collaboration**: CRDT with property tests is rigorous, but the user-visible result (real-time co-editing) is parity with everyone in this space.

---

## Where email-hub is behind

| Gap | Severity | Cost to close |
|---|---|---|
| **No customers/case studies/logos publicly** | CRITICAL | $0 — needs 1 published case study from Merkle/agency work (with permission) |
| **No GTM motion** (no pricing, no demo flow, no G2 listing, no comparison content) | CRITICAL | 1–2 weeks |
| **No public template/inspiration gallery** | HIGH | 4–8 weeks to build a 50–100 brand inspiration site |
| **No external MCP server** | HIGH (Knak just claimed this) | 4–6 weeks to ship v1 |
| **No SDK / white-label embed** | HIGH | 3–6 months |
| **No AMP for Email** | MEDIUM | 6–8 weeks (and only matters if ICP includes interactive-email use cases) |
| **Localisation depth** | MEDIUM | Tolgee is in; deepening to 300+ locales narrative is ~4 weeks |
| **No published cost / BYOL story** | MEDIUM | 1 week to package adapters as a marketing benefit |
| **Maintenance surface** | HIGH | Cut scope. See [monetization.md](./monetization.md) Path #2. |

---

## The matrix verdict

**Engine layer (Stensul/Knak don't even talk about):** email-hub leads on 9 of 9 measured capabilities.

**Product layer (drag-drop, approvals, builder polish):** parity.

**Distribution layer (customers, logos, pricing, integrations breadth, SDK, MCP, gallery):** email-hub trails by miles.

**Conclusion:** the engine investment is real and ahead of market. Without distribution it doesn't matter commercially. The next two documents — [monetization.md](./monetization.md) and [leverage-strengths.md](./leverage-strengths.md) — focus on closing the distribution gap and turning the engine wins into compounding moats.
