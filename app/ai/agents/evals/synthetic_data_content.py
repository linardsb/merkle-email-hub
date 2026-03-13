"""
Synthetic test data for the Content agent.

Each test case provides realistic input text, operation, and constraints.
Spam trigger words sourced from real blocklists (Mailmeteor, Moosend, HubSpot).
Industry contexts reflect actual email marketing scenarios.
"""

# ---------------------------------------------------------------------------
# Real spam trigger words (sourced from industry blocklists)
# ---------------------------------------------------------------------------
SPAM_TRIGGERS = {
    "urgency": [
        "act now",
        "limited time",
        "urgent",
        "expires today",
        "order now",
        "don't hesitate",
        "final call",
        "immediately",
        "this won't last",
        "while supplies last",
        "last chance",
        "hurry",
        "before it's too late",
    ],
    "financial": [
        "make $",
        "earn cash",
        "easy income",
        "instant earnings",
        "double your wealth",
        "financial freedom",
        "save big money",
        "100% free",
        "free money",
        "no cost",
        "no obligation",
    ],
    "clickbait": [
        "click here",
        "click below",
        "amazing deal",
        "can't miss",
        "you will not believe",
        "incredible deal",
        "once in a lifetime",
        "congratulations",
        "you've been selected",
        "winner",
    ],
    "pressure": [
        "buy now",
        "call now",
        "apply now",
        "sign up free",
        "limited offer",
        "exclusive deal",
        "special promotion",
        "risk-free",
        "guaranteed",
        "no catch",
        "100% guaranteed",
    ],
}

# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

CONTENT_TEST_CASES = [
    # =========================================================================
    # SUBJECT LINE tests
    # =========================================================================
    {
        "id": "content-001",
        "dimensions": {
            "operation": "subject_line",
            "industry": "ecommerce_fashion",
            "tone_target": "luxury_aspirational",
            "constraint_pressure": "tight_character_limit",
        },
        "input": {
            "operation": "subject_line",
            "text": (
                "We're launching our Fall/Winter 2025 collection featuring Italian leather "
                "goods, cashmere knitwear, and limited-edition silk accessories. The collection "
                "drops October 15 with a VIP early access window for loyalty members starting "
                "October 12. Price range $120-$890. Target: affluent women 28-45."
            ),
            "tone": "luxury_aspirational",
            "brand_voice": (
                "Understated elegance. Never shout. Use sophisticated vocabulary. "
                "Avoid exclamation marks. Favor European sensibility."
            ),
            "num_alternatives": 5,
        },
        "expected_challenges": [
            "40-60 character limit is tight for luxury messaging",
            "must avoid ALL CAPS and spam words like 'limited'",
            "brand voice demands understatement — no urgency language",
            "should front-load value proposition",
        ],
    },
    {
        "id": "content-002",
        "dimensions": {
            "operation": "subject_line",
            "industry": "b2b_saas",
            "tone_target": "professional_formal",
            "constraint_pressure": "must_avoid_spam_words",
        },
        "input": {
            "operation": "subject_line",
            "text": (
                "We're offering a free trial of our enterprise analytics platform. "
                "Features include real-time dashboards, automated reporting, and AI-powered "
                "insights. The free trial lasts 30 days with no credit card required. "
                "We want to drive signups from CTOs and VPs of Engineering."
            ),
            "tone": "professional",
            "brand_voice": None,
            "num_alternatives": 3,
        },
        "expected_challenges": [
            "must avoid 'free trial', 'no credit card', 'sign up free' — all spam triggers",
            "should reframe value without trigger words",
            "professional tone for C-suite audience",
        ],
    },
    {
        "id": "content-003",
        "dimensions": {
            "operation": "subject_line",
            "industry": "healthcare",
            "tone_target": "empathetic_supportive",
            "constraint_pressure": "legal_compliance_required",
        },
        "input": {
            "operation": "subject_line",
            "text": (
                "Reminder email for patients who haven't scheduled their annual wellness check. "
                "We want to encourage scheduling without being pushy. Must comply with healthcare "
                "communication guidelines — no guarantees about outcomes, no medical claims. "
                "Clinic name: Meridian Health Partners."
            ),
            "tone": "empathetic",
            "brand_voice": (
                "Warm, caring, professional. We're a partner in your health journey, "
                "not an authority figure. Never use fear-based language."
            ),
            "num_alternatives": 3,
        },
        "expected_challenges": [
            "healthcare compliance — no outcome guarantees",
            "empathetic without being patronizing",
            "no urgency/fear language per brand voice",
            "avoid spam triggers while encouraging action",
        ],
    },
    # =========================================================================
    # PREHEADER tests
    # =========================================================================
    {
        "id": "content-004",
        "dimensions": {
            "operation": "preheader",
            "industry": "travel_hospitality",
            "tone_target": "playful_witty",
            "constraint_pressure": "tight_character_limit",
        },
        "input": {
            "operation": "preheader",
            "text": (
                "Subject line: 'Your next adventure starts with a click'\n\n"
                "Email promotes our summer travel deals — 40% off flights to Mediterranean "
                "destinations (Greece, Croatia, Italy, Spain). Booking window: June 1-15. "
                "Travel dates: July through September. Includes hotel bundles."
            ),
            "tone": "playful",
            "brand_voice": None,
            "num_alternatives": 3,
        },
        "expected_challenges": [
            "40-130 characters",
            "must complement subject line, not repeat it",
            "playful tone in very limited space",
            "avoid 'limited time' spam trigger for booking window",
        ],
    },
    # =========================================================================
    # CTA tests
    # =========================================================================
    {
        "id": "content-005",
        "dimensions": {
            "operation": "cta",
            "industry": "nonprofit",
            "tone_target": "empathetic_supportive",
            "constraint_pressure": "must_avoid_spam_words",
        },
        "input": {
            "operation": "cta",
            "text": (
                "Year-end fundraising email for a children's literacy nonprofit. "
                "Asking for donations to fund reading programs in underserved schools. "
                "Tax-deductible donations. Goal: $500K by December 31. "
                "Want the CTA to inspire generosity without guilt-tripping."
            ),
            "tone": "empathetic",
            "brand_voice": (
                "Hopeful, not desperate. Center the children's stories, not the ask. "
                "Every dollar is a page turned."
            ),
            "num_alternatives": 5,
        },
        "expected_challenges": [
            "2-5 words only",
            "action verb start",
            "must avoid 'Donate Now', 'Give Now' (too generic)",
            "must avoid 'Click Here', 'Submit'",
            "benefit-focused per brand voice",
        ],
    },
    {
        "id": "content-006",
        "dimensions": {
            "operation": "cta",
            "industry": "ecommerce_fashion",
            "tone_target": "urgent_fomo",
            "constraint_pressure": "must_avoid_spam_words",
        },
        "input": {
            "operation": "cta",
            "text": (
                "Flash sale email — 24 hours only, up to 60% off select styles. "
                "We want the button to create urgency and drive clicks. "
                "But it absolutely cannot use 'Buy Now', 'Act Now', 'Shop Now' "
                "or any spam trigger phrases."
            ),
            "tone": "urgent",
            "brand_voice": None,
            "num_alternatives": 5,
        },
        "expected_challenges": [
            "create urgency in 2-5 words WITHOUT spam triggers",
            "avoid 'Buy Now', 'Act Now', 'Shop Now', 'Click Here'",
            "benefit-focused action verb",
            "balance FOMO with deliverability safety",
        ],
    },
    # =========================================================================
    # BODY COPY tests
    # =========================================================================
    {
        "id": "content-007",
        "dimensions": {
            "operation": "body_copy",
            "industry": "financial_services",
            "tone_target": "authoritative_expert",
            "constraint_pressure": "legal_compliance_required",
        },
        "input": {
            "operation": "body_copy",
            "text": (
                "Email announcing a new high-yield savings account product. "
                "APY: 4.75% (variable). FDIC insured up to $250K. No minimum balance. "
                "No monthly fees. Online-only account. Mobile app with instant transfers. "
                "Must include: rates may change, FDIC disclaimer, not investment advice. "
                "Target audience: millennials with $10K+ in checking who aren't maximizing savings."
            ),
            "tone": "authoritative",
            "brand_voice": (
                "Smart money, made simple. We're the advisor who speaks plainly. "
                "Data-first, jargon-lite. Confidence without arrogance."
            ),
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "scannable short paragraphs",
            "hook > value > proof > CTA hierarchy",
            "must include legal disclaimers naturally",
            "avoid 'guaranteed', '100% free', 'no risk' spam triggers",
            "financial compliance language woven in",
            "authoritative but accessible per brand voice",
        ],
    },
    {
        "id": "content-008",
        "dimensions": {
            "operation": "body_copy",
            "industry": "food_beverage",
            "tone_target": "casual_friendly",
            "constraint_pressure": "no_constraints",
        },
        "input": {
            "operation": "body_copy",
            "text": (
                "Monthly newsletter for a craft brewery. This month: new IPA release "
                "(Haze Runner, 6.8% ABV, notes of mango and pine), upcoming taproom events "
                "(trivia night every Thursday, live music Saturday Oct 18), "
                "merch drop (winter beanies and pint glasses), and a homebrew tip of the month."
            ),
            "tone": "casual",
            "brand_voice": None,
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "casual tone without being sloppy",
            "organize 4 different topics in scannable format",
            "conversational 'you/your' language",
            "single primary CTA despite multiple topics",
        ],
    },
    # =========================================================================
    # REWRITE tests
    # =========================================================================
    {
        "id": "content-009",
        "dimensions": {
            "operation": "rewrite",
            "industry": "b2b_saas",
            "tone_target": "professional_formal",
            "constraint_pressure": "strict_brand_voice",
        },
        "input": {
            "operation": "rewrite",
            "text": (
                "Hey there!! We're SO excited to tell you about our AMAZING new feature!!! "
                "It's gonna totally change the way you do business. Click here to learn more "
                "about this incredible opportunity that you absolutely can't miss. "
                "ACT NOW before it's too late — this is a LIMITED TIME offer that won't last. "
                "Trust us, you'll regret not signing up. FREE for the first month!!!"
            ),
            "tone": "professional",
            "brand_voice": (
                "Precision in every word. We don't oversell — we demonstrate value. "
                "Data speaks louder than adjectives. B2B enterprise voice."
            ),
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "complete tone transformation needed",
            "remove ALL spam triggers (8+ present)",
            "remove excessive punctuation",
            "remove ALL CAPS words",
            "preserve core message: new feature announcement",
            "rewrite as professional B2B communication",
        ],
    },
    # =========================================================================
    # SHORTEN tests
    # =========================================================================
    {
        "id": "content-010",
        "dimensions": {
            "operation": "shorten",
            "industry": "real_estate",
            "tone_target": "professional_formal",
            "constraint_pressure": "tight_character_limit",
        },
        "input": {
            "operation": "shorten",
            "text": (
                "We are absolutely thrilled and delighted to announce that we have just recently "
                "listed a truly spectacular and absolutely stunning new property that has just "
                "come on the market in the highly sought-after and very desirable neighborhood "
                "of Westwood Hills. This beautiful and elegant home features an impressive and "
                "spacious 4 bedrooms and 3 full bathrooms, a completely renovated and modernized "
                "gourmet chef's kitchen with top-of-the-line stainless steel appliances, "
                "gorgeous and pristine hardwood floors throughout the entire main level, "
                "and a breathtaking and amazing backyard oasis complete with a sparkling "
                "heated swimming pool and a fully equipped outdoor entertainment area. "
                "The property is conveniently and ideally located within easy walking distance "
                "of top-rated and highly acclaimed schools, trendy and popular shopping, "
                "and beautiful and well-maintained parks."
            ),
            "tone": None,
            "brand_voice": None,
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "reduce by 30-50%",
            "remove redundant adjective pairs",
            "remove filler phrases ('absolutely', 'truly')",
            "preserve key selling points",
            "maintain professional tone",
        ],
    },
    # =========================================================================
    # TONE_ADJUST tests
    # =========================================================================
    {
        "id": "content-011",
        "dimensions": {
            "operation": "tone_adjust",
            "industry": "ecommerce_fashion",
            "tone_target": "playful_witty",
            "constraint_pressure": "strict_brand_voice",
        },
        "input": {
            "operation": "tone_adjust",
            "text": (
                "Dear Valued Customer,\n\n"
                "We wish to inform you that our annual end-of-season clearance event "
                "will commence on the 15th of January. During this period, selected items "
                "from our Autumn/Winter collection will be available at reduced prices, "
                "with discounts ranging from 30% to 70% off the recommended retail price.\n\n"
                "We encourage you to visit our website or retail locations at your earliest "
                "convenience to take advantage of these savings.\n\n"
                "Yours sincerely,\nThe Fashion Team"
            ),
            "tone": "playful_witty",
            "brand_voice": (
                "We're your stylish best friend, not a corporate letter. "
                "Emoji-friendly (but tasteful). Pop culture references welcome. "
                "Short sentences. Energy!"
            ),
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "complete register shift: formal corporate -> playful friend",
            "preserve ALL factual content (dates, percentages, items)",
            "adjust vocabulary and sentence structure",
            "match brand voice precisely",
            "no spam triggers despite sale language",
        ],
    },
    # =========================================================================
    # EXPAND tests
    # =========================================================================
    {
        "id": "content-012",
        "dimensions": {
            "operation": "expand",
            "industry": "healthcare",
            "tone_target": "empathetic_supportive",
            "constraint_pressure": "legal_compliance_required",
        },
        "input": {
            "operation": "expand",
            "text": (
                "New telehealth service available. Book appointments online. "
                "See a doctor from home. Most insurance accepted."
            ),
            "tone": "empathetic",
            "brand_voice": (
                "Healthcare should feel human. Plain language, warm delivery. "
                "Acknowledge the patient's time and comfort."
            ),
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "add detail without making medical claims",
            "maintain warm/empathetic tone",
            "no 'guaranteed' or outcome promises",
            "do not introduce unsupported claims",
            "expand from ~20 words to ~80-100 words",
        ],
    },
    # =========================================================================
    # Edge case: multilingual context
    # =========================================================================
    {
        "id": "content-013",
        "dimensions": {
            "operation": "subject_line",
            "industry": "ecommerce_fashion",
            "tone_target": "casual_friendly",
            "constraint_pressure": "multilingual_context",
        },
        "input": {
            "operation": "subject_line",
            "text": (
                "Flash sale email for our Canadian audience. "
                "Brand operates in English and French Canada. "
                "Subject line should work for English speakers but be mindful "
                "that preheader will be in French. "
                "Sale: 25% off with code HIVER25. Free shipping on orders over $75 CAD. "
                "Products: winter outerwear and accessories."
            ),
            "tone": "casual",
            "brand_voice": None,
            "num_alternatives": 3,
        },
        "expected_challenges": [
            "culturally aware for Canadian market",
            "no French words in subject (preheader handles that)",
            "CAD currency context",
            "avoid spam triggers around 'free shipping'",
        ],
    },
    # =========================================================================
    # Edge case: PII in source text
    # =========================================================================
    {
        "id": "content-014",
        "dimensions": {
            "operation": "rewrite",
            "industry": "financial_services",
            "tone_target": "professional_formal",
            "constraint_pressure": "legal_compliance_required",
        },
        "input": {
            "operation": "rewrite",
            "text": (
                "Hi John Smith (john.smith@email.com), your account #4829-3847 "
                "at 142 Oak Street, Springfield has been approved for a credit limit "
                "increase to $15,000. Call us at 555-0123 to confirm. "
                "Your SSN ending in 7842 was used for verification."
            ),
            "tone": "professional",
            "brand_voice": None,
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "MUST replace ALL PII with placeholders",
            "[NAME], [EMAIL], [PHONE], [ADDRESS]",
            "must NOT include account numbers or SSN",
            "security rules are absolute",
        ],
    },
    # =========================================================================
    # LENGTH GUARDRAIL stress tests (task 11.19)
    # =========================================================================
    {
        "id": "content-015",
        "dimensions": {
            "operation": "subject_line",
            "industry": "ecommerce_fashion",
            "tone_target": "luxury_aspirational",
            "constraint_pressure": "tight_character_limit",
            "output_length": "at_boundary",
        },
        "input": {
            "operation": "subject_line",
            "text": (
                "Introducing our new Spring 2026 collection of Italian leather "
                "handbags and accessories, now available with complimentary monogramming "
                "for loyalty members during the exclusive early access preview event."
            ),
            "tone": "luxury_aspirational",
            "brand_voice": (
                "Sophisticated, understated. Every word should feel considered. "
                "No exclamation marks. European sensibility."
            ),
            "num_alternatives": 5,
        },
        "expected_challenges": [
            "HARD LIMIT: must stay under 60 characters",
            "rich brief tempts long subject lines (58+ chars)",
            "luxury tone needs concise elegance, not verbose descriptions",
            "5 alternatives all must pass the 60-char limit",
        ],
        "expected_length_behavior": "at_boundary — all alternatives must be ≤60 chars",
    },
    {
        "id": "content-016",
        "dimensions": {
            "operation": "cta",
            "industry": "b2b_saas",
            "tone_target": "professional_formal",
            "constraint_pressure": "must_avoid_spam_words",
            "output_length": "over_max",
        },
        "input": {
            "operation": "cta",
            "text": (
                "We want a CTA button for our enterprise security compliance platform. "
                "The button should communicate that clicking will start a guided demo "
                "of the automated compliance monitoring and real-time threat detection features. "
                "Target audience: CISOs and security directors at Fortune 500 companies."
            ),
            "tone": "professional",
            "brand_voice": (
                "Enterprise-grade trust. Precision over personality. "
                "Every word should convey authority and reliability."
            ),
            "num_alternatives": 5,
        },
        "expected_challenges": [
            "HARD LIMIT: 5 words maximum",
            "complex product tempts verbose CTAs (6-7 words)",
            "must start with action verb",
            "avoid generic 'Learn More', 'Click Here'",
            "professional tone in minimal word count",
        ],
        "expected_length_behavior": "over_max — brief tempts 6-7 word CTAs",
    },
    {
        "id": "content-017",
        "dimensions": {
            "operation": "expand",
            "industry": "healthcare",
            "tone_target": "empathetic_supportive",
            "constraint_pressure": "legal_compliance_required",
            "output_length": "ratio_violation",
        },
        "input": {
            "operation": "expand",
            "text": "Book your telehealth appointment today.",
            "tone": "empathetic",
            "brand_voice": (
                "Healthcare should feel human. Plain language, warm delivery. "
                "Acknowledge the patient's time and comfort."
            ),
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "HARD LIMIT: output must not exceed 150% of original",
            "very short input (39 chars) — 150% = 58 chars max",
            "tempts LLM to add full paragraph of benefits",
            "must expand meaningfully within tight ratio",
            "healthcare compliance — no outcome guarantees",
        ],
        "expected_length_behavior": "ratio_violation — short input makes 150% cap very tight",
    },
    {
        "id": "content-018",
        "dimensions": {
            "operation": "shorten",
            "industry": "real_estate",
            "tone_target": "professional_formal",
            "constraint_pressure": "tight_character_limit",
            "output_length": "under_min",
        },
        "input": {
            "operation": "shorten",
            "text": (
                "We are absolutely thrilled to present this magnificent and truly extraordinary "
                "five-bedroom estate nestled in the highly prestigious and sought-after enclave "
                "of Pacific Heights, featuring panoramic bay views from every single floor, "
                "a chef's kitchen with imported Italian marble countertops and professional-grade "
                "Viking appliances, a temperature-controlled wine cellar housing up to 500 bottles, "
                "and an award-winning landscaped garden designed by the renowned horticulturist "
                "Elena Marchetti. The property spans an impressive 6,200 square feet across "
                "three meticulously appointed levels, includes a detached two-car garage with "
                "an EV charging station, and is situated within walking distance of the finest "
                "dining establishments, boutique shopping destinations, and highly rated schools."
            ),
            "tone": None,
            "brand_voice": None,
            "num_alternatives": 1,
        },
        "expected_challenges": [
            "HARD LIMIT: output must be 50-70% of original length",
            "bloated input with redundant adjectives",
            "must preserve key selling points (beds, location, features)",
            "shorten output must not over-cut below 50%",
        ],
        "expected_length_behavior": "under_min — LLM may over-cut below 50% threshold",
    },
]
