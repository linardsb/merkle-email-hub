# Competitor profiles

Sixteen competitors grouped by what they actually compete *for*. Lumping them together is misleading — Beefree and Stensul aren't going after the same buyer.

---

## Group A — Enterprise marketing-production platforms (hardest competitors)

These own the "governance + brand control + AI + approvals + ESP integration" pitch to large marketing organisations. They're where email-hub would land if it tried to be a generalist.

### Stensul

- **URL:** [stensul.com](https://stensul.com), [stensul.com/ai](https://stensul.com/ai/)
- **Positioning:** "Governed Creation™ Platform" — enterprise email + landing page + AI with built-in compliance
- **Funding:** $60.5M total. Series C $34.5M in 2023. ([PitchBook](https://pitchbook.com/profiles/company/144178-48))
- **Pricing:** Custom enterprise. Reportedly four tiers (Growth/Team/Business/Enterprise). No free trial. Prepare for high prices. ([Capterra](https://www.capterra.com/p/247817/stensul/), [Blocks review](https://useblocks.io/blog/stensul-review/))
- **AI features:**
  - Email Generator — brief → fully-produced draft (announced June 2025)
  - Text Re-generator — refine specific text fields, tone shifts
  - Title / Subject / Preheader / CTA / Image / Alt Text generators
  - **BYOL "coming soon"** — route AI through Azure OpenAI, AWS Bedrock, Google Gemini using customer's own LLM contracts
  - 90% claimed reduction in campaign creation time
- **Integrations:** 100+ — Salesforce/SFMC, Adobe (GenStudio + Creative Cloud), Slack, OpenAI, DAMs
- **Customers:** BlackRock, Cisco, Demandbase, Siemens, Thomson Reuters, Equifax. Milwaukee Bucks (33% increase in requests, halved creation time), Mindbody (16x reduction), Bisnow (180x reduction, 10-min email)
- **Documented weaknesses (per [Blocks](https://useblocks.io/blog/stensul-review/) and [Dyspatch](https://www.dyspatch.io/blog/dyspatch-vs-stensul/) comparisons):**
  - No code editor
  - Partial mobile responsiveness
  - No AMP for Email
  - No direct ESP export (still "coming soon" per some sources)
  - No native dynamic content / customer profiles for testing
  - Limited conditional logic
  - Limited API
  - Enterprise-only pricing — unaffordable for small teams

### Knak

- **URL:** [knak.com](https://www.knak.com), [knak.com/mcp](https://knak.com/mcp/)
- **Positioning:** "Marketing production platform" for enterprise — emails + landing pages + workflow + AI
- **Funding:** Multiple rounds; specific totals not in public search results
- **Pricing:** Reportedly starts ~$10,000/year (per [Knak alternatives](https://knak.com/knak-alternatives/) ecosystem articles)
- **AI features:**
  - **Knak AI** — embedded asset creation co-pilot for "flawless emails and landing pages, the first time"
  - **Knak MCP (April 2026)** — ChatGPT and Claude can now call Knak directly to produce on-brand emails. Currently in Alpha. ([CMSWire](https://www.cmswire.com/the-wire/knak-makes-enterprise-marketing-production-callable-by-ai-agents/))
  - Figma plugin → Marketo / SFMC / Eloqua workflow
  - Dynamic content via form fields (no Velocity script needed)
- **Integrations:** Marketo, Eloqua, Pardot, SFMC, Adobe Campaign, Adobe Journey Optimizer, Open API
- **Customers / scale:** OpenAI, Meta, Google, Palo Alto Networks (scaled from 2 to ~200 builders). 1,000,000+ assets created. 95% faster TTM. 22-min average email.
- **Strategic move:** Knak MCP is the most aggressive competitive move in the market. They're betting that AI agents (not humans) will be the primary "callers" of email production tools within 18 months. They want to own that integration layer.

### Dyspatch

- **URL:** [dyspatch.io](https://www.dyspatch.io)
- **Positioning:** Centralized email production hub for cross-functional teams
- **Pricing:** Starter $149/mo, Teams $499/mo, Teams+ custom (account manager, premium support, SLA, SAML SSO). 10% annual discount. ([Dyspatch](https://www.dyspatch.io))
- **AI features:**
  - **Scribe AI** — turns marketing briefs and Figma designs into campaign-ready content
  - "Automate the heavy lifting while amplifying creative vision"
- **Standout features:**
  - **AMP for Email** — pre-coded interactive Apps in Email, claims 5x engagement
  - **300+ locales** — leading platform for localisation, claims 250% faster TTM
  - Smartling translation integration
  - Litmus testing integrated
  - Modular design system (reusable blocks)
  - Conditional templating with auto-compatibility insertion
  - Customer profiles for dynamic-content testing
- **Integrations:** Braze, Iterable, SFMC, Pardot, SendGrid, Marketo, HubSpot, Eloqua, Klaviyo, Mailchimp, AWS Pinpoint/SES
- **Customers:** Less prominent logos than Stensul/Knak, but established
- **Why they matter:** Dyspatch's published [Dyspatch vs. Stensul](https://www.dyspatch.io/blog/dyspatch-vs-stensul/) comparison page is a goldmine — every feature gap they call out in Stensul (responsive auto-gen, localisation, AMP, conditional logic, dynamic content, modern API) is a feature you should consider whether email-hub matches

---

## Group B — Figma → email plugins (your most direct architectural competitors)

These are the closest match to email-hub's `design_sync` module. If email-hub commercialises the Figma-to-ESP pipe, these are the head-to-head opponents.

### Email Love

- **URL:** [emaillove.com/figma-plugin](https://emaillove.com/figma-plugin), [emaillove.com](https://emaillove.com)
- **Positioning:** Figma plugin → MJML → 13 ESPs, built by 15-year email experts
- **Pricing:** Free / $19 Starter / $35 Growth / Enterprise (with 1:1 onboarding, custom design system, Slack support)
- **AI features:**
  - **AI Studio** (Growth+) — syncs Figma design system, generates complete email templates from text brief, uses actual brand colors/fonts/components
- **Architecture:** MJML output for cleaner code, 100+ pre-built components, brand-aware AI generation
- **ESP integrations (broadest in this category):** SFMC, Braze, Iterable, HubSpot, Klaviyo, Campaign Monitor, Pardot, Marketo, MoEngage, OneSignal, Loops, Zeta, Customer.io
- **Brand assets:** Email Love also runs a 6,000-brand inspirational email gallery as marketing top-of-funnel — this drives plugin sign-ups
- **Why they matter:** **Closest direct competitor to email-hub's design_sync.** Broader ESP coverage. Established. If you commercialise the Figma niche, you compete head-on.

### Composa

- **URL:** [composa.email](https://composa.email)
- **Positioning:** "Design in Figma. Build emails in Composa." Persistent structural bridge from Figma design system → emails
- **Pricing:** Waitlist (= still pre-launch / private beta)
- **AI features:** AI reads campaign brief → selects components from synced design system → assembles production-ready first draft with copy/CTAs/links pre-populated
- **Architecture:** **MJML-powered structural bridge** (their phrasing). When you change a component in Figma and re-sync, every email using that component updates. This is identical in concept to what email-hub's design_sync does at the design system level.
- **ESP integrations:** Braze, Iterable, SFMC, Marketo, Klaviyo, HubSpot
- **Why they matter:** **Architecturally the most similar to email-hub.** Earlier stage (waitlist), narrower scope. Beatable if you ship publicly first; threat if they raise funding faster.

### Hypermatic Emailify

- **URL:** [hypermatic.com/emailify](https://www.hypermatic.com/emailify/)
- **Positioning:** Figma plugin → HTML, 30+ email clients
- **Pricing:** Free trial / $49/mo Pro / $99/mo Pro Bundle (12 plugins). 30-day refund.
- **AI features:** Translation only — OpenAI, Claude, Gemini for multi-language emails. Excel (XLSX) bulk localisation.
- **ESP integrations:** 30+ — MailChimp, Klaviyo, HubSpot, Salesforce, SendGrid, Braze, Campaign Monitor, ActiveCampaign + webhooks
- **Customers / scale:** 129,000+ designers and marketers. Claims to save "20+ hours weekly."
- **Why they matter:** Mass-market reach. If email-hub goes the Figma plugin route, they're the volume baseline you have to beat on quality.

### MigmaAI

- **URL:** [migma.ai/figma-to-email](https://migma.ai/figma-to-email)
- **Pricing:** Free (5 designs/month) / Premium / Enterprise
- **AI features:** One-click Figma → HTML conversion, 95% accuracy claim. **Knowledge Base** that learns brand patterns from uploaded materials.
- **ESP integrations:** Mailchimp, Campaign Monitor, HubSpot, others
- **Why they matter:** Lower-end of the Figma-to-email space. Their "knowledge base learning" pattern is something email-hub could do better with the existing knowledge agent infrastructure.

### Knak's Figma plugin

- **URL:** [knak.com/blog/figma-to-marketo](https://knak.com/blog/figma-to-marketo/)
- **Positioning:** Figma plugin embedded in Knak's enterprise platform — flexbox→nested-tables conversion preserving design intent
- **Why they matter:** Knak has both the Figma-to-email plugin AND the enterprise governance platform AND now MCP. They're attempting to occupy three slices of the market simultaneously.

### DesignFast / EmailGenie

- Long tail of Figma community plugins. Not strategic individually but indicate the space is crowded.

---

## Group C — No-code mass-market builders

Different segment (SMB and mid-market) but they own the volume. Not direct competitors unless email-hub goes downmarket.

### Beefree

- **URL:** [beefree.io](https://beefree.io)
- **Pricing:** Free / Professional $25–30/mo / Business $134–160/mo / Enterprise custom
- **AI:** "BEE AI" — referenced but not deeply detailed; content generation, brand controls
- **Customers:** Headspace, L'Oreal, Netflix, Volvo, UNICEF, Save the Children, Bosch, Eli Lilly. **10,000+ companies.** Embedded in **1,000+ SaaS applications via SDK.** ([Crunchbase](https://www.crunchbase.com/organization/bee-083d))
- **Stats they advertise:** 81% of users 3x faster, 75% seamless tech-stack integration, 64% +11% CTR, 73% payback in 3 months
- **G2 awards:** "Best Est. ROI" Enterprise, "Easiest to use"
- **Why they matter:** **Beefree SDK** is the dark-horse moat. Most second-tier ESPs that "have a builder" are running Beefree under the hood. If email-hub wants distribution at scale, embedding through SDK is one play; competing with Beefree on it is harder than it looks.

### Stripo

- **URL:** [stripo.email](https://stripo.email)
- **Features:** Drag-and-drop + simultaneous code editing, 1,650+ free HTML templates, 300+ pre-built modules, AI assistant
- **AI:** Email writing, subject line generator, scheduling helper, copy generation
- **Integrations:** **90+ ESPs** (one-click export), Zapier, webhook export, Email-on-Acid testing integration
- **Customers / scale:** **1,700,000+ users.** Brands include Maersk, Adobe, Microsoft, Spotify
- **Why they matter:** Volume leader. ESP integration breadth is best-in-class.

### Chamaileon

- **URL:** [chamaileon.io](https://chamaileon.io)
- **Features:** Visual editor + design system + dynamic content + role-based permissions
- **AI:** Not advertised
- **Integrations:** 40+ — Mailchimp, HubSpot, Pardot, Marketo, Braze, SendGrid, Klaviyo, ActiveCampaign + Zapier
- **Claims:** 90% faster TTM, 99% client compatibility
- **Why they matter:** Mid-market, no AI = at risk of being lapped within 12 months unless they ship.

### Blocks (useblocks.io)

- **URL:** [useblocks.io](https://useblocks.io)
- **Pricing:** ~$16.80/mo starting (per their Stensul-comparison content)
- **Features:** 150+ templates across 27 industries, ChatGPT-style AI assistant, live chat support
- **Why they matter:** Aggressive low-end. Demonstrates that "AI assistant" alone is not a moat.

---

## Group D — Code-centric / developer tools

Different audience (developers) but worth knowing what the code-savvy slice looks like.

### Parcel

- **URL:** [parcel.io](https://parcel.io)
- **Features:** Email-aware code editor, 80+ inbox previews, design systems, transformers (CSS inlining, minification), test sends, public share links
- **AI:** **None.**
- **Pricing:** Not on homepage; "no credit card required"
- **Why they matter:** They own the developer-team email-coding slice without AI. If AI becomes table-stakes (it will), they have to ship — they're a likely future entrant in the AI-email space.

### MJML / Maizzle (frameworks)

- Not products, but the frameworks the products are built on. email-hub already uses Maizzle. Email Love and Composa use MJML. This is the open-source layer.

---

## Group E — ESPs that bake AI in (the platform threat)

The "platform absorbs the feature" risk. If these ship deep AI email creation, the wrapper-layer dies.

### Klaviyo (K:AI / Composer)

- **URL:** [klaviyo.com/composer](https://www.klaviyo.com/composer), [klaviyo.com/solutions/ai](https://www.klaviyo.com/solutions/ai)
- **AI features:**
  - **Composer** — full campaign generation from a prompt: audience, copy, email, SMS, flows, all grounded in brand and customer data
  - **K:AI Marketing Agent** — digests transactional data → hyper-personalised shopping experiences, generates fresh strategic on-brand content, weekly campaign ideas
  - **Brand voice guidelines** — voice descriptor titles + writing rules feed into all AI-generated content ([help.klaviyo.com](https://help.klaviyo.com/hc/en-us/articles/35873068949147))
- **Scale:** 193,000 brands
- **Vertical focus:** Ecommerce
- **Why they matter:** Klaviyo owns the ecommerce vertical. If you go after ecommerce DTC brands, you're competing with K:AI not the other AI-email tools.

### Salesforce Marketing Cloud + Einstein

- **URL:** [help.salesforce.com Einstein generative AI](https://help.salesforce.com/s/articleView?id=mktg.mc_anb_einstein_use_genai.htm)
- **AI features:**
  - **Einstein Generative AI** (Winter '24+) — generates email subject lines and body content
  - **Einstein Copy Insights** — set up brand identities, **up to 10 brand personalities** (Professional, Casual + 8 custom)
  - **Typeface integration** — content asset creation in Content Builder
  - Dynamic content blocks for personalisation by audience and geography
- **Why they matter:** **Adobe and Salesforce can absorb the entire AI-email category internally.** Stensul's strategic move (integrate with Adobe, support BYOL via Azure/Bedrock/Gemini) is a partner-not-compete play. Email-hub doesn't have that relationship — that's both a risk and (for the agency-internal hypothesis) an irrelevance.

### Adobe GenStudio

- **URL:** [business.adobe.com/products/genstudio](https://business.adobe.com/products/genstudio/main.html) (page returned timeout during research)
- **Positioning:** Content supply chain for enterprise marketing — workflow + AI + brand + asset management
- **AI features:** Firefly-powered content generation, brand-on-brand outputs
- **Why they matter:** GenStudio is Adobe's bid for the entire content-creation stack including email. Stensul integrates with it. Email-hub doesn't, and probably never will at the same depth without Adobe partnership.

### HubSpot

- **AI features:** Generate full emails from prompts, AI subject line suggestions, AI image generation
- **Why they matter:** Mid-market and SMB. CRM-native. Default for many marketers; AI features are good enough for most.

### Customer.io (AI Agent — added April 2026)

- **URL:** [customer.io/platform/agent](https://customer.io/platform/agent), [customer.io/learn/announcements/biggest-ai-marketing-release](https://customer.io/learn/announcements/biggest-ai-marketing-release)
- **Positioning:** "AI Agent that does the work, not just the talking." Autonomous campaign lifecycle management from conversation.
- **AI features:**
  - **Persistent memory** — brand voice, goals, preferences, guardrails, compliance requirements retained across sessions
  - **End-to-end campaign execution** — constructs triggers, content, timing, workflow logic from natural-language prompts
  - **Performance analysis** — surfaces underperforming messages, compares metrics in plain language
  - **Compounding intelligence** — system sharpens with each prompt
  - **MCP support** — "built for agents, not just humans, works with any AI tool using MCP, CLI, API or webhooks"
  - **LLM actions in workflows** — add AI-powered steps to campaign workflows (sentiment analysis, translation, personalised recommendations)
- **Operates within:** Customer.io's existing Journeys, Audience segmentation, Design Studio, Analytics
- **Trust indicators:** 9,000+ brand users, GDPR + HIPAA + SOC certified
- **Customers / case studies:** Notion (50% onboarding open rate), Livestorm (4% increase in winback conversions), Klar (14% increase in first transactions)
- **Pricing:** 14-day free trial; specific tiers not on landing page
- **Why they matter:** **Customer.io's MCP support (alongside Knak's April 2026 MCP launch) confirms the architectural shift.** ESPs are absorbing AI campaign creation natively. Customer.io customers are now far less likely to need a Stensul/Knak/email-hub layer — the platform's Agent does it. They don't reach into Figma fidelity (their Design Studio is template-based, not design-system-synced from Figma), so email-hub's visual-verification differentiator survives, but the addressable Customer.io customer subset shrinks dramatically. Same dynamic for Klaviyo K:AI, SFMC Einstein, HubSpot, and now Customer.io.

### Iterable

- **URL:** [iterable.com/features/ai](https://iterable.com/features/ai/)
- **Positioning:** Enterprise customer engagement platform for lifecycle programs
- **AI features:**
  - **Studio** — drag-and-drop journey builder
  - **Journey Assist** — generative AI creates journey workflows from natural-language prompts
  - **Send Time Optimization** — per-user optimal send time
  - **Predictive Goals** — ML-identified users likely to act/churn
  - **Nova AI suite** — capable but reportedly less deep than top competitors
- **Vertical focus:** Enterprise SaaS, fintech, consumer tech
- **Why they matter:** Iterable's AI is journey-shaped not content-shaped. Less of a direct content threat, more of a "platform that owns the customer" threat.

---

## Group F — Specialists worth knowing

### Mailmodo

- **URL:** [mailmodo.com](https://www.mailmodo.com)
- **Positioning:** **AMP for Email leader** — interactive emails (polls, forms, games)
- **AI features:** AI Email Template Generator, AI Automation Builder, AI Segment Generator, AI Campaign Analyzer
- **Customers / case studies:**
  - foundit (job marketplace): 400% more registrations with interactive forms
  - bigbasket (grocery): 6× email engagement with interactive poll
  - BluSmart, Razorpay, HobSpace
- **Integrations:** 40+
- **Why they matter:** **If interactive AMP email becomes table-stakes (it might in 2027), they leapfrog every static-HTML platform including email-hub.** AMP is the one feature that genuinely changes the email medium and email-hub doesn't address it.

### Litmus

- **URL:** [litmus.com](https://www.litmus.com)
- **Positioning:** Email previewing + QA + accessibility leader
- **Pricing:** ~$500/mo (jumped from previous lower tiers in 2025)
- **Features:** 100+ client previews, dark mode HTML errors in Builder, accessibility checks (color contrast, alt text, headings, screen reader simulation), automated QA checklist
- **Why they matter:** **Email-hub's 14 QA checks compete with Litmus directly on substance.** Litmus is what enterprise teams pay $500/mo for. If email-hub productises QA-as-a-service, Litmus is the benchmark.

### Email on Acid

- **URL:** [emailonacid.com](https://www.emailonacid.com)
- **Pricing:** ~$74/mo basic, unlimited testing
- **Features:** 100+ client previews, dark mode, accessibility on Premium tier
- **Why they matter:** Lower-cost Litmus alternative. Same QA niche.

### Mail Bakery

- **URL:** [mailbakery.com](https://mailbakery.com)
- **Business model:** **Service agency, not SaaS.** Hand-coded email templates from PSD/Sketch/Figma/PDF designs. No AI.
- **Why they matter:** They're a different category — not a competitor to a software product. But their existence is signal: there's still a real market for "we'll just hand-code your email template" services. If email-hub can deliver that with engine support, that's a real product.
