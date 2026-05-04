# Monetisation paths — five strategies + fastest-path-to-revenue

This document answers two questions:
1. What are my options if I don't want to abandon this project?
2. **What do I need to do to monetise it in the shortest time possible?**

---

## TL;DR

**Fastest path to first dollar:** sell email production as a service, using email-hub as your delivery engine. **Day 1 to first revenue: 7–14 days.** Charge $5–15k per campaign. Position as "the studio that delivers 99%-fidelity Figma-to-ESP with verified visual QA." This is **Path #5 below**.

**Fastest path to $10k MRR with software:** Path #2 below — productise design_sync as a focused Figma → ESP pipe. **30 days to landing page + Figma plugin v1, 90 days to first 10 paying customers at $99–299/mo seat = $1k–$3k MRR. Realistic to $10k MRR by month 6** if you nail one ICP.

**Highest-EV path long-term:** Path #1 (Merkle-internal moat) if agency-internal is true; otherwise Path #3 (open-source engine + paid hosting) for defensibility, or Path #4 (acquihire) for exit.

**Don't do:** Path generalist-SaaS-vs-Stensul. You will lose by inches every quarter.

---

## The five strategic paths, ranked

### Path #1 — Merkle-internal moat (HIGHEST EV if agency-internal hypothesis is true)

**What:** Keep email-hub private. Use it as a competitive weapon in agency pitches and as a margin lever on email production work.

**Pitch to Merkle leadership:** "We have a proprietary AI email engine that delivers visually-verified 99%-fidelity Figma → ESP at a unit cost no Stensul-licensed competitor can match. This is Merkle's email moat for the next 3 years."

**Monetisation mechanics:**
- Win pitches you'd otherwise lose against agencies running Stensul/Knak (each retainer = $200k–$2M/year)
- Take on email-only retainers (less competitive bidding)
- Cut email production cost by 50–70% on existing accounts → margin expansion
- Bill premium for "AI-verified email" service line ($800–$2,500 per email vs. industry $200–$500 hand-coded)

**Time to revenue:** **0 days** — the value is realised through existing client engagements; no external sales cycle required.

**Risk:** dependent on Merkle leadership recognising and investing in maintenance. If team that built it leaves, the engine ages.

**This is the recommended path if Merkle-internal context is real.** Don't externalise. Keep the moat.

---

### Path #2 — Specialist Figma → ESP fidelity SaaS (RECOMMENDED if commercialising)

**What:** Compete head-on with Email Love and Composa specifically — not Stensul/Knak. Position: **"The only Figma-to-ESP pipeline with iterative VLM visual verification that actually matches your design."**

**Scope cuts (this is the hardest part):**
- ✅ Keep: design_sync, visual_verify loop, brand pipeline, tree compiler, 4–5 ESP exports (Klaviyo, Braze, HubSpot, SFMC, Iterable), basic QA (5 of 14 checks: html_validation, dark_mode, accessibility, link, image)
- ❌ Drop or de-prioritize: builder polish, workflow orchestration, Tolgee/TMS, scheduling, plugin system, 9 of 14 QA checks, AMP, AI-evaluator agent (keep internally, don't market), CRDT collaboration, the entire `cms/` frontend (replace with a focused Figma plugin)

**Pricing:**
- Free tier: 5 conversions/month
- Pro: $99/mo per seat — unlimited conversions, all ESP exports, brand pipeline
- Team: $299/mo per seat — design system sync, approvals, 5 QA checks
- Enterprise: $1,500–5,000/mo per workspace — BYOL, SAML SSO, on-prem option

**Target customer (ICP):** in-house design teams at 50–500-person companies that already use Figma for email design and have $5k–$50k/month email production budget. Likely vertical wedges: B2B SaaS, fintech (regulated, fidelity-critical), DTC ecommerce in Europe (Klaviyo+Braze territory).

**Time to revenue:**
- Week 1–2: Cut scope. Strip frontend to a minimum landing page + Figma plugin shell.
- Week 3–4: Ship Figma plugin v1 + simple web app for output review/ESP push.
- Week 4: Launch landing page with 60-second demo video of visual verification loop.
- Week 5–6: Open free tier signup. Convert 3–5 design partners (offer 6-month free Pro in exchange for case study).
- Week 8–12: First 10 paying customers ($99–$299/mo). **MRR: $1k–$3k by month 3.**
- Month 4–6: First Enterprise customer at $2k–$5k/mo. **MRR: $5k–$10k by month 6.**
- Month 12: $30k–$50k MRR target.

**Realistic ARR by year 2:** $500k–$1.5M if execution is good and one ICP locks.

**Risk:** Composa exits beta well-funded; Email Love adds visual verification; you under-invest in marketing. Mitigation: ship the demo video first, before building.

**Why this is the recommended commercial path:** the visual verification loop is a real, demoable, communicable differentiator. Nobody else has it. The niche is small enough to win.

---

### Path #3 — Open-source the engine, sell paid hosting (Maizzle/Penpot model)

**What:** Open-source the converter + visual verify + QA engine + tree compiler under MIT or Apache 2.0. Sell hosted runs, premium support, enterprise SSO, on-prem deployment.

**Why it works:** Maizzle has shown the pattern (open-source framework → paid hosting/services). Penpot has shown design-tool-as-OSS works. The eval-calibration discipline + visual verify loop are research artifacts that get cited and earn credibility.

**Monetisation:**
- Hosted SaaS: $0 free / $79 Pro / $499 Team / Enterprise custom
- Premium support: $1k–$5k/mo for SLA + dedicated channel
- Custom integrations: $10k–$50k for new ESP/MAP connectors
- Training/consulting: $2k/day

**Time to revenue:**
- Month 1: Refactor for OSS release (license headers, docs, contributor guide, separation from Merkle-specific code)
- Month 2: Public launch on Show HN, Product Hunt, designer Twitter, email-marketing communities
- Month 3–6: Build community, ship hosted SaaS, first paying customers
- Month 12: $5k–$20k MRR

**Risk:** OSS communities are high-investment. Without a dedicated DevRel/community manager, the project stalls. Adoption depends on emotional proof — "this thing works" — which the visual verify loop provides.

**Why this is appealing:** highest defensibility. Engine quality is what wins; copying is hard because the eval discipline isn't in the source code, it's in the calibration data.

---

### Path #4 — Acquihire / strategic license

**What:** Don't compete. Sell.

**Plausible acquirers:**
- **Knak** — they need the visual verification loop and the eval discipline. They have the customers; you have the tech.
- **Stensul** — they're well-funded ($60.5M) and would value the BYOL/agent-pipeline depth.
- **Beefree** — they'd want an enterprise/governance upgrade. They're in 1,000+ SaaS apps and have the distribution.
- **Adobe** — strategic fit with GenStudio. Long shot but the eval system would be valuable.
- **Litmus** — their core is QA; email-hub's 14 checks + calibrated evals are an upgrade path.
- **Merkle/Dentsu itself** (if not already internal) — productise within agency tech stack.

**Pitch:** "We have a calibrated AI email engine with visual verification at ~99% fidelity. We're 18 months ahead of public competitor capability. Acquire the team and the tech for 12–24-month time-to-market savings."

**Time to revenue:** 6–12 months from first conversation to closed deal.

**Realistic outcome:** $2M–$10M acquihire (small team, strong tech, no customers). Higher if there are customers and revenue.

**Why consider:** the "good engineer with no customers" position is exactly what acquihires monetise. If you don't want to do GTM, this is the rational path.

---

### Path #5 — FASTEST: Done-for-you email production service

**What:** Don't sell software. Sell email campaigns as a delivered service, using email-hub as your delivery platform.

**Pitch:** "Send us your Figma file and brief. We deliver a tested, brand-compliant, visually-verified, ESP-ready email in 24 hours for $5,000."

**Why it's the fastest:**
- No software product to ship
- No sales cycle to build (services sell on referrals + freelance platforms day one)
- No support burden (you control delivery)
- Premium pricing supported by the visual-verify quality story
- Cash flow positive from week 1

**Pricing:**
- Single email: $5k flat ($1k for simple, $15k for hero campaigns)
- Monthly retainer: $15k/month for 5 emails
- Migration project: $25k to migrate a brand from old templates to verified email-hub-rendered ones

**Channels:**
- Toptal, Contra, MarketerHire, Upwork (start day 1, takes ~7 days for first inbound)
- Cold outreach to design teams at series B+ startups with active Figma libraries
- LinkedIn posts demoing the visual verification loop
- Twitter/X demo videos
- Direct outreach to brands using Klaviyo/Braze/SFMC complaining about email production speed on community forums

**Time to revenue:** **7–14 days** to first invoice. **30 days to $10k–$30k cash collected** if you push hard on outreach.

**Realistic year-1 outcome:** $200k–$500k revenue as a one-person operation. Margins are 70–80%. No equity dilution. No investors.

**Why this is the fastest:** services scale linearly with effort, but the startup cost is zero and the validation is immediate. **You also learn what enterprise email teams actually pain about**, which is the research input you'd need before building Path #2 anyway.

**Strategic upside:** every campaign delivered = 1 case study. After 20 campaigns, you have the proof points to launch Path #2 or Path #3 from a position of evidence, not theory.

---

## Path comparison at a glance

| Path | Time to first $ | Year-1 revenue range | Year-3 revenue range | Defensibility | Capital required |
|---|---|---|---|---|---|
| #1 Merkle-internal moat | 0 days | $0 (margin expansion only) | $0 (margin expansion only) | Highest (private) | $0 |
| #2 Specialist SaaS | 8–12 weeks | $50k–$200k | $1M–$3M | Medium | $50k–$200k own time |
| #3 Open-source + hosting | 4–6 months | $20k–$100k | $500k–$1.5M | Highest (community) | $100k+ for DevRel |
| #4 Acquihire | 6–12 months | $0–$2M (one event) | $2M–$10M | n/a | $0 |
| **#5 Done-for-you service** | **7–14 days** | **$200k–$500k** | **$1M–$2M (with team)** | Low (depends on you) | **$0** |

---

## The fastest path: 14-day plan to first revenue

This is concrete. Execute in order.

### Days 1–3: Build the marketing artifact

**The single most important thing you don't have yet is a 60-second demo video of the visual verification loop running on a real Figma file.**

- Pick one of email-hub's existing snapshot regression cases (MAAP, Starbucks, or Mammut)
- Record screen: Figma → run pipeline → low-fidelity first render → verification loop fixing 12 specific issues → 99% match diff overlay
- Voice over with the value prop: "Designers ship pixel-perfect Figma. AI agents render. Visual verification iterates until 99% match. Zero hand-coding."
- Cut to 60 seconds. Upload to YouTube + Twitter/X + LinkedIn.

### Days 4–7: Build a one-page landing page

- Domain: pick something neutral (not "email-hub" if Merkle-owned IP is sensitive). Suggestions: pixelmail.studio, fidelity.email, verified.email, brandkit.email
- Hero: 60-second video + one-line value prop + "Get a $5,000 email in 24 hours" CTA
- Below the fold: how it works (Figma in → 9-agent pipeline → visual verify → QA → ESP-ready), 3 sample case excerpts, pricing ($5k single / $15k retainer), email/calendly form
- Stack: Vercel + Next.js. Ship in 2 days.

### Days 5–10: Outbound

Run two parallel motions:

**Inbound channel seeding (cheap, slow but compounding):**
- Post the demo video on Twitter/X, LinkedIn, Hacker News (Show HN: "AI email generation with visual fidelity verification")
- Post in r/EmailDesign, r/EmailMarketing
- Submit to Product Hunt (timing for week 2)
- Write a Substack post on "Why most AI email tools render at 60–80% fidelity" with the verification loop as the answer

**Outbound (drives first revenue fastest):**
- 100 cold emails to design directors / heads of growth / heads of CRM at series B+ B2B SaaS or DTC ecommerce companies. Template:
  > "I noticed [company] uses [Klaviyo/Braze/Iterable]. We deliver Figma-to-ESP emails with AI visual verification at 99% fidelity in 24 hours. Sample work: [video link]. First campaign $5k. Worth a 15-min call?"
- 20 conversations on Toptal, Contra, MarketerHire (set rates at $5k/email and $200/hour for ad-hoc)
- 5 LinkedIn DMs/day to email designers / email-ops leads at companies in your network

### Days 11–14: Close first deal

- Most deals will need 1–3 calls. Prepare a 15-minute deck: problem (production is slow + low-fidelity) → solution (video) → process (Figma → 24h delivery → ESP push) → pricing → next step
- First close should land $2.5k–$10k (often discounted on first deal as a "case study price"). That's fine — the case study is worth more than the discount.
- Deliver in 24h. Document the entire pipeline run as a case-study artifact (with permission).

### Day 14+: Compound

After the first delivery:
- Publish the case study (with permission)
- Use the case study in next 100 cold emails — conversion rates 5–10× from cold-with-proof vs. cold-without-proof
- Convert the first customer to monthly retainer ($15k/month)
- Aim for 3 retainer customers ($45k MRR) by month 3 = $540k ARR run rate as a one-person service business

### What to track

- **Inbound:** video views, landing page visits → form fills (target 2% landing page conversion)
- **Outbound:** cold-email reply rate (target 5–10%), call-to-close rate (target 20–30%)
- **Delivery:** time from Figma → ESP-ready (target <24h), QA pass rate (target 100%), customer NPS
- **Retention:** 1-month, 3-month, 6-month retainer renewal rate

---

## Common monetisation mistakes to avoid

1. **Don't build a builder.** Beefree, Stripo, and Stensul have spent collectively 30+ years polishing email drag-and-drop builders. You will not catch up. Cut your `cms/` frontend scope ruthlessly.

2. **Don't market to marketers via SEO content.** That game is won. Stensul/Knak/Beefree have 5+ years of "best email builder" content. Compete on demos and case studies, not blog SEO.

3. **Don't price too low.** $99/mo positions you as Beefree-tier. The visual verification loop is a premium claim — own it. $299–$999/mo is the right band if you're going SaaS. $5k–$15k/email is the right band if you're going service.

4. **Don't try to sell to Fortune 100 first.** Stensul/Knak own those relationships. Sell to companies where the buyer can decide on a $500–$3,000/month bill in a week, not 6-month enterprise procurement. Series B+ B2B SaaS is the sweet spot.

5. **Don't pitch "AI email" — pitch "verified Figma-to-ESP."** AI email is commodity (Klaviyo K:AI, SFMC Einstein). Verified visual fidelity from Figma is not. Pitch the difference.

6. **Don't ignore Knak MCP.** If they ship MCP support to general availability before you have any market presence, they own the "AI agents call us for email production" narrative. Either ship your own MCP server within 6 weeks (Path #2 + extension) or accept that Path #5 (services) is your fastest answer.

7. **Don't keep building features.** The engine is ahead of market. The product is behind. Spend 80% of the next 90 days on distribution (landing page, video, outreach, case studies) and 20% on engine improvements.

---

## Decision flow

```
Is this Merkle-internal?
├── Yes → Path #1 (use as moat). Stop here. Don't externalise.
└── No  → Want fastest revenue?
         ├── Yes (need cash now) → Path #5 (service business). 7-day plan above.
         └── Want to build a software business?
              ├── Yes → Path #2 (specialist SaaS). 8-week plan.
              │        └── After Path #5 traction → Path #2 with case studies.
              └── Want to optimise for exit / defensibility?
                   ├── Acquihire → Path #4
                   └── Open source + hosting → Path #3
```

**Most likely best sequence (if not Merkle-internal):**
1. Path #5 for 90 days → cash flow + customer evidence + ICP validation
2. Path #2 starting at month 4 → SaaS leveraging the case studies from Path #5
3. Optionally Path #3 in year 2 → open-source the engine for moat once SaaS has traction
4. Path #4 (acquihire) becomes the exit option from any of the above

---

## Risks to monitor

- **Knak MCP general-availability launch.** Currently Alpha. If GA before you have presence, the AI-callable production niche closes.
- **Stensul ships visual verification.** They're well-funded; this is the most likely competitor to copy the visual verify loop within 12 months.
- **Adobe GenStudio absorbs more of the email category.** Means agency-internal Path #1 stays defensible (agencies want to own client relationships, not be Adobe resellers); SaaS Path #2 gets harder over time.
- **Composa ships out of waitlist.** They're closest architecturally. If they raise a big Series A, they out-execute.
- **AMP for Email becomes table-stakes.** If Mailmodo's interactive-email category jumps to mainstream in 2027, every static-HTML platform — including email-hub — has to ship AMP or lose deals.

---

**Bottom line:** the fastest monetisation is services (Path #5, 7–14 days to first dollar). The most defensible long-term commercial path is specialist SaaS (Path #2). The highest-EV path if Merkle-internal is to keep email-hub as Merkle's moat (Path #1). The default doomed path is generalist SaaS competition with Stensul/Knak — don't take it.
