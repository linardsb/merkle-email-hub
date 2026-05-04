# Dual-track: Merkle-internal AND startup

**Selected framing.** Email-hub is both: an internal tool that makes Merkle better at email production, and a commercial product the user wants to sell externally.

This is the most common framing among technical founders building inside agencies. It's also the framing where most projects die — not from technical or market reasons, but from **unmanaged tensions** between the two tracks. This document is about managing those tensions deliberately.

---

## Read this first — the IP conversation is the gating step

**Before writing a line of SaaS marketing copy, have the IP/commercial-rights conversation with Merkle leadership in writing.**

Most agency employment contracts include an IP assignment clause that makes anything you build during employment, on company resources, related to the company's line of business, automatically the agency's property. Email-hub almost certainly fits all three criteria.

If you start a SaaS without resolving this, one of three bad things eventually happens:
1. **Merkle blocks the launch** when they realise. You lose 6–12 months of work.
2. **Merkle lets it run, then claims ownership** when there's revenue or a sale. Worst-case you owe them everything you've earned.
3. **A Merkle competitor (Publicis, WPP, Omnicom, Dentsu sibling agency) buys your SaaS** and uses it against Merkle's pitch wins. Merkle leadership feels betrayed; your career inside Merkle ends; the agency might still claim IP.

The conversation is uncomfortable but the alternative is worse. It's also an opportunity — if framed as a joint venture, Merkle becomes your first customer and a strategic backer, not a blocker.

### Possible IP structures (rank-ordered by founder upside)

| Structure | Founder upside | Merkle upside | Likelihood Merkle agrees |
|---|---|---|---|
| **A. Founder spins out, Merkle invests + becomes anchor customer** | High — own the IP and the company, raise on Merkle's brand | Moderate — equity stake + free internal use as preferred customer | Moderate. Requires Merkle leadership to see the vision. |
| **B. Open core: OSS engine + commercial hosting/extensions** | Medium — own the SaaS company, OSS limits acquihire upside, broader adoption | High — perpetual free internal use, shared maintenance with community | High. OSS removes most legal worries; Merkle gets to keep using it. |
| **C. Merkle owns IP, exclusive commercial license to founder** | Medium — own the SaaS revenue, no IP risk, but Merkle controls direction | High — IP retention + revenue share | Moderate. Common in agency settings; Merkle legal will negotiate revenue share hard. |
| **D. Joint venture (Merkle and founder co-own SaaS entity)** | Low–Medium — diluted upside, shared decisions | High — direct equity in upside | High in principle, slow in practice. Can take 6–12 months to finalize. |
| **E. Status quo (you build SaaS quietly without permission)** | Negative expected value | Negative | n/a — don't do this |

### What to ask for in the conversation

1. **Written confirmation of which work is commercialisable** (e.g., the engine, the calibration system, the visual verify loop) and which is Merkle-only (client-specific workflows, client-branded templates, client data integrations).
2. **A timeline for an IP assignment or licensing agreement** (target: 60 days from first conversation).
3. **Founder commitment** about how SaaS work will be done (e.g., evenings/weekends, separate machine, separate accounts) until the legal structure is clear.
4. **A non-compete carve-out** specifying that Merkle will not block the SaaS in agency competitors (Publicis/WPP/etc.) once launched, in exchange for a commercial benefit to Merkle.

### Don't do until this is resolved

- Don't register a SaaS company
- Don't buy a domain that conflicts with Merkle's IP claim
- Don't accept any external customer payment
- Don't pitch investors
- Don't announce on Twitter/LinkedIn

You can absolutely:
- Continue building inside Merkle for Merkle's benefit
- Document case studies internally (they become commercial assets later)
- Do passive market research (this folder is fine)
- Have informal conversations with potential SaaS customers ("validation interviews")

---

## Once IP is resolved — the operating model

Assuming Structure A or B (founder gets commercial rights), the operating model has three layers:

### Layer 1: The shared engine

The core technical work — visual verify loop, calibrated evals, multi-agent DAG, brand pipeline, tree compiler, QA checks, design_sync — lives in **one repo, one codebase, one set of tests.**

Both products consume this engine. **No fork.** Forking is what kills dual-track projects within 18 months. Two codebases means two bug lists, two test suites, two roadmaps, and eventually two teams. You can't sustain that.

The engine is owned by the licensing entity (Merkle for Structure C, founder's company for Structure A, OSS project for Structure B).

### Layer 2: Merkle-internal product

A thin layer above the engine that's specific to Merkle's agency operations:
- Merkle's client-list integration
- Merkle-branded templates and component libraries
- Merkle workflows (specific approval chains, billing integration, project-management hooks)
- Merkle's customer-data exports (e.g. their CMA platform integration if any)
- Merkle SSO and access control

This stays private to Merkle. Lives behind their firewall. Uses internal-only branding ("Merkle Email Hub" or whatever the agency calls it).

### Layer 3: SaaS product

A different thin layer above the same engine, but built for general-purpose external customers:
- Generic onboarding (no client-list assumption)
- Public component library (not Merkle-specific)
- Standard workflows (configurable, not Merkle-specific)
- Generic ESP integrations (no agency-specific bridges)
- Public branding (a neutral name; **not "merkle-email-hub"** — you cannot use Merkle's name in a SaaS product)

This is the commercial product. Has its own domain, billing, support, marketing.

### How to keep the layers honest

The big risk is "engine drift": the engine accumulates Merkle-specific assumptions (e.g. hardcoded client list paths, Merkle-only auth, Merkle-specific approval workflows). Once that happens, the SaaS layer can't function without weird workarounds, and you fork.

**Rules to prevent drift:**
- The engine has zero references to Merkle, client names, internal endpoints, or agency-specific URLs
- The Merkle layer can depend on the engine; the engine can NOT depend on the Merkle layer
- The SaaS layer can depend on the engine; the engine can NOT depend on the SaaS layer
- All Merkle-specific configuration is in the Merkle layer's config, not engine config
- New engine features have to be useful for both Merkle and SaaS — if a feature is Merkle-only, it goes in the Merkle layer

This is unglamorous architecture work but it's the single highest-leverage decision in dual-track operating.

---

## The phased plan

### Phase 0 — IP resolution (Days 1–60)

**Goal:** signed agreement defining what you can commercialise.

- Day 1: schedule the conversation with Merkle leadership
- Day 1–14: prepare the pitch (use [monetization.md](./monetization.md) Path #2 numbers as the upside; emphasize Merkle benefit in Structure A or B)
- Day 14–60: negotiate, get signature
- **Hard rule: no SaaS work until signed.** Continue building inside Merkle. Use the time for market research and validation interviews.

### Phase 1 — Internal validation (Months 1–3, can overlap with Phase 0)

**Goal:** turn Merkle's existing email production into the SaaS validation engine.

- Run email-hub on every Merkle email production for the next 90 days
- Track metrics that will become marketing claims: time-to-deliver, fidelity score, revisions required, cost per email
- Get permission from 2–3 Merkle clients (with comms team approval) to publish anonymised case studies
- Identify which 1–2 verticals Merkle's email work hits hardest (financial services? DTC ecommerce? B2B SaaS?). That becomes your SaaS launch ICP.
- Document at least 3 stories of "Stensul/Knak/Litmus customer pain we solved" that you can use in SaaS sales conversations
- **Wire internal MCP into one Merkle workflow.** Pick an existing Merkle AI tool or approval step that would benefit from calling email-hub (e.g. brand check, fidelity score). One concrete internal MCP caller in 60 days validates the API surface and generates a "MCP works in production" anecdote — at zero commercial exposure since it's Merkle-only.

**This is free customer discovery.** Most SaaS founders pay $50k–$200k for what you get from your day job.

### Phase 2 — Architectural separation (Months 2–4, parallel with Phase 1)

**Goal:** split the codebase cleanly into engine + Merkle layer + SaaS layer.

- Audit current code for Merkle-specific assumptions; refactor them into the Merkle layer
- **MCP server lives in the engine layer.** Both Merkle layer and SaaS layer consume it via a single API surface. No fork — same tools, same schemas, same versioning. Add a thin auth/tenancy adapter so internal callers (Merkle) and external callers (SaaS) hit different code paths for auth but the same code path for tool execution.
- Create the SaaS layer skeleton (separate package, generic config, public-facing API)
- Set up CI to verify the engine has no Merkle/SaaS dependencies (a simple grep test)
- Build the SaaS-tier database schema (multi-tenant, generic, no client-list assumption)
- Pick the SaaS brand name (NOT containing "merkle"; suggestions: pixelmail.studio, fidelity.email, verified.email, brandkit.email — register the .com if available)

This is a 2-month engineering project done in evenings/weekends, OR an explicit Merkle-funded project if Structure A includes Merkle paying for the architectural split as their contribution.

### Phase 3 — Service-business launch using the same engine (Months 3–4)

**Goal:** generate first external revenue using [monetization.md](./monetization.md) Path #5 — done-for-you services. **You can do this with the SaaS layer in early state — services don't need a polished product.**

- Run the 14-day fastest-path-to-revenue plan from monetization.md
- First 3 deals serve as additional case studies and ICP validation
- Revenue: $30k–$100k by month 4
- This funds Phase 4 (the SaaS product) without external capital

### Phase 4 — SaaS soft launch (Months 4–6)

**Goal:** ship the SaaS product publicly, leveraging case studies from Merkle (with permission) and Phase 3 service customers.

- Domain + landing page + 60-second video of the visual verification loop
- Open free tier signup, convert 5 design partners (free Pro for 6 months in exchange for case study)
- **Ship external MCP server as part of launch** — auth, multi-tenancy, public tool docs. Wraps existing internal MCP (`app/mcp/server.py`) with OAuth/API keys + per-tenant rate limits + audit logging. Exposes 4–6 tools (visual_verify, apply_brand, qa_check, design_sync_convert, repair_html, score_fidelity).
- Public launch: Show HN, Product Hunt, designer Twitter, email-marketing communities
- Target: 10 paying customers ($99–$299/mo) by end of month 6
- **Critical: do NOT compete with Merkle for clients.** If a SaaS prospect overlaps with Merkle's pitch list, refer them to Merkle. This is the goodwill that keeps Structure A/B intact.

**Why MCP ships at Phase 4 not Phase 5:** Knak Alpha (April 2026) and Customer.io (April 2026) shipped MCP. The window where MCP is a differentiator is months 4–8 of 2026; after that it's a checkbox. Internal MCP can ship earlier (Phase 1–2) since it's Merkle-only and not commercially exposed. External MCP requires Phase 0 IP resolution + the SaaS commercial entity, so it can't ship before Phase 4.

### Phase 5 — Scale (Months 6–12)

**Goal:** $30k–$100k MRR; first Enterprise customer; defensive moves on Knak MCP narrative.

- Ship MCP server (response to Knak's April 2026 move) — month 7
- Open-source the EmailTree schema + correction applicator (per [leverage-strengths.md](./leverage-strengths.md)) — month 9
- First Enterprise deal at $2k–$5k/mo — month 8
- Hire first SaaS engineer once MRR > $20k — month 10

---

## The five dual-track tensions and how to manage each

### Tension 1: Time conflict

**Symptom:** Merkle work takes priority during day; SaaS suffers; or vice versa.

**Management:**
- Set a hard rule: 4 evenings/week + Saturday on SaaS until $10k MRR. This is sustainable for ~12 months.
- Once at $10k MRR, negotiate part-time at Merkle (3 days/week) to scale SaaS to $50k MRR.
- Once at $50k MRR, full transition to SaaS. Merkle becomes anchor customer, not employer.
- Don't try to "do both at full intensity forever." That fails by month 6.

### Tension 2: Client conflict

**Symptom:** A SaaS prospect is also a Merkle client target. Or a Merkle client asks for a feature you'd want in SaaS.

**Management:**
- **Hard rule: SaaS does not sell to companies that are active Merkle pitch targets.** Document the list with Merkle BD; refresh quarterly.
- Conversely, if a Merkle client requests a SaaS feature, that's free product input — build it in the engine where both layers benefit.
- If conflict is unavoidable (large prospect interested in both), refer them to Merkle first; if Merkle declines, you can pursue.

### Tension 3: Brand conflict

**Symptom:** Merkle clients see your SaaS, get confused about whose tech they're buying. Or worse — they think Merkle is selling SaaS instead of agency services and pull retainers.

**Management:**
- **Different domain. Different brand. Different visual identity.** No cross-references on either site.
- LinkedIn personal profile: don't promote SaaS on the same channels as Merkle work (separate Twitter, separate newsletter, separate LinkedIn posting cadence).
- Merkle's website doesn't mention the SaaS. SaaS website doesn't mention Merkle.
- Case studies on the SaaS site are anonymised: "Fortune 500 financial services brand" not "BlackRock via Merkle."

### Tension 4: Roadmap conflict

**Symptom:** Merkle wants Feature A (e.g. specific client integration); SaaS market wants Feature B (e.g. AMP for Email). You can only build one this quarter.

**Management:**
- All client-specific work goes in the Merkle layer, not the engine. Doesn't conflict with SaaS roadmap.
- Engine roadmap is decided by SaaS market signal + leverage-strengths.md sequencing.
- If a Merkle ask requires engine changes, evaluate: does it benefit SaaS too? If yes, build. If no, rebuild it as a Merkle-layer extension or decline.

### Tension 5: Information leakage

**Symptom:** Merkle client data ends up in SaaS training data, eval calibration, or example outputs. Or SaaS bug reports leak Merkle internal information.

**Management:**
- **Strict separation of data:**
  - Merkle production traces stay in Merkle's infrastructure
  - SaaS production traces stay in SaaS's infrastructure
  - The engine's eval system uses synthetic + golden + opt-in customer data only — never live client data without explicit per-client consent
- PII redaction (you already have this — Phase 44.12) is non-optional in both deployments
- Calibration dataset: any data labelled from Merkle work needs explicit Merkle approval before being used in SaaS

---

## Realistic outcome distribution

Given the framing (Merkle-internal + startup, structure pending), realistic outcomes by year 3:

| Outcome | Probability | What it looks like |
|---|---|---|
| **Best case: SaaS reaches $1M+ ARR with Merkle as ongoing anchor customer** | 15–25% | 30–60 paying SaaS customers, Merkle gets equity or revenue share, founder transitions to full-time SaaS. Strategic acquihire option opens. |
| **Good case: Service business + Merkle moat, no SaaS scale** | 30–40% | $300k–$700k/year service revenue, Merkle keeps email-hub internally, founder stays at Merkle or freelance. SaaS launched but doesn't scale; engine continues compounding. |
| **Acquihire** | 10–20% | Knak/Stensul/Beefree/Adobe acquires the team and tech for $2M–$10M; Merkle gets paid out per IP agreement. |
| **Stalemate** | 20–30% | Tensions kill momentum; SaaS never launches publicly or shutters at year 1. Merkle keeps using it internally. Founder learns; moves on. |
| **Bad case: IP dispute / Merkle blocks** | 5–15% | Phase 0 didn't happen or went badly; Merkle claims everything; founder loses. |

**The single biggest predictor of which bucket you end up in is whether Phase 0 (IP resolution) is done before Phase 1.** Skip Phase 0 and the bad case probability triples.

---

## What success looks like at end of year 1

If executed well:

- **Phase 0 signed:** founder has commercial rights to engine + SaaS layer; Merkle keeps internal use rights and gets revenue share or equity
- **Phase 1 done:** 3 case studies (anonymised, with permission); 90 days of Merkle production data validates the fidelity claims; vertical ICP identified
- **Phase 2 done:** clean separation; engine has zero Merkle dependencies; SaaS layer has its own brand and infra
- **Phase 3 done:** $50k–$150k in service revenue from external customers
- **Phase 4 done:** 10–25 paying SaaS customers; $5k–$15k MRR
- **Phase 5 starting:** MCP server shipped; first OSS release of EmailTree schema; first Enterprise deal in pipeline
- **Merkle internally:** still using email-hub; productivity gains documented; relationship with founder unchanged

That's a realistic, executable outcome from the dual-track. It requires sustained effort but doesn't require luck.

---

## What to do this week

1. **Write a one-page proposal for Merkle leadership.** Frame: "I've built something that's both Merkle's competitive moat and potentially a commercial product. Here's how we structure it so Merkle benefits both ways. Can we talk?" Reference Structure A or B from the table above. Send by end of week.

2. **Don't write any SaaS code or marketing this week.** Use the time for the proposal and informal Merkle conversations.

3. **Identify 2 trusted advisors** outside Merkle who can review the IP structure when Merkle proposes one — typically a startup lawyer and a startup operator who's done a similar split. Don't sign without external review.

4. **Read [monetization.md](./monetization.md) Path #5** once more. Your fastest revenue is services — and services can run alongside Phase 0 because they don't compete with Merkle (you just pick prospects Merkle isn't pitching). $5k cash by week 3 is feasible even before Phase 0 is signed, if Merkle leadership approves it as a side activity.

---

## Honest closing note

The dual-track is the highest-EV path *if executed correctly*. It's the lowest-EV path if rushed or if IP isn't resolved. The thing that makes dual-track work isn't engineering or product or marketing — it's the relationship with Merkle leadership.

If you can't have an honest, clear conversation with Merkle leadership about what you've built and what you want to do with it, you don't have a dual-track project — you have a conflict waiting to be discovered. Most "dual-track" startups fail here, not at product or sales.

The product is ready. The engineering is ahead of market. The remaining variable is whether the human conversation gets done.
