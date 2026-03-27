---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_email-spam-score-dom-reference.md sections 16, 20 -->
<!-- Last synced: 2026-03-13 -->

# Spam Trigger Phrases & Content Signals — L3 Reference

## Category 1: Urgency & Pressure
- act now, act immediately
- limited time, limited offer
- don't miss out, don't delete
- hurry, urgent, immediately
- once in a lifetime, one time only
- while supplies last, while they last
- expires, expiring, deadline
- last chance, final chance
- now or never, today only
- time is running out, running out

## Category 2: Money & Financial
- buy now, buy direct, buy today
- no cost, no fees, no obligation
- 100% free, completely free, totally free
- free access, free gift, free trial, free membership
- double your, triple your
- earn money, earn extra, extra income
- fast cash, quick cash, easy money
- make money, making money
- credit card, no credit check
- lowest price, best price, cheap, discount, bargain, save big
- investment, return on investment
- no catch, no strings attached
- risk free, without risk

## Category 3: Claims & Guarantees
- 100% guaranteed, guarantee, guaranteed
- no questions asked, satisfaction guaranteed
- money back, full refund
- certified, approved, verified
- as seen on, featured in
- doctor approved, scientifically proven
- miracle, amazing, incredible
- revolutionary, breakthrough, secret
- exclusive deal, special promotion
- winner, winning, you won, congratulations
- selected, been selected, you have been chosen

## Category 4: Formatting Triggers
- ALL CAPS words (more than 2 consecutive) — SLIGHT negative per instance; cumulative
- Multiple exclamation marks (!!!) — SLIGHT negative
- Dollar signs ($$$) — SLIGHT negative
- Percentage symbols followed by "off" (%%% off)
- Excessive use of "free" (3+ times in one email)
- Red colored text — associated with spam aesthetics
- Excessive emoji (especially 🔥💰🎉💵 in subject lines or headings)

## Category 5: Action Phrases
- click here, click below, click now, click this link
- order now, order today
- sign up free, subscribe now
- call now, call free, call today
- apply now, apply online
- join now, join millions
- visit our website
- download now, install now

## Category 6: Phishing-Related Text (HIGH Impact)
- verify your account, confirm your identity, update your information
- your account has been suspended/compromised/locked
- enter your password/SSN/credit card
- dear customer (generic greeting instead of personalized)
- dear friend, dear valued customer
- important information regarding
- regarding your account
- unfilled merge tags (`{FIRST_NAME}`, `{NAME}`) — broken template indicates mass mailing

## Hidden Text Techniques to Avoid
These content techniques trigger SEVERE/HIGH negative spam scoring:
- Text color matching background color (white on white, etc.) — SEVERE
- Near-matching colors (`color: #fefefe` on `background: #ffffff`) — HIGH
- `color: transparent` — HIGH
- `font-size: 0` or `font-size: 1px` — SEVERE/HIGH
- `display: none` or `visibility: hidden` on text elements — HIGH
- `text-indent: -9999px` — HIGH (pushes text off-screen)
- `line-height: 0` on text — HIGH (collapses to invisible)
- Unicode obfuscation (lookalike characters: "Ⅴіаgrа" instead of "Viagra") — SEVERE
- Zero-width characters within words to break up keywords — HIGH
- HTML entities used to spell spam words (`&#86;&#105;&#97;`) — SEVERE

## Content in `alt` Attributes
- `alt` text containing spam keywords — Negative
- `alt` text that IS the entire email message — MODERATE negative
- Keyword-stuffed `alt` text (`alt="BUY NOW CHEAP DISCOUNT SALE"`) — Negative

## Positive Content Signals (Improve Deliverability)
- Personalized greeting (merge tags resolved: "Hi Sarah" not "Hi {FNAME}")
- Physical mailing address in footer
- Unsubscribe link in footer
- Privacy policy link
- Company name and registration info
- Reply-to address that accepts replies
- Links to sender's own domain (consistent with `From` address)
- `alt` text on meaningful images
- Balanced image-to-text ratio (60%+ text recommended)
- `List-Unsubscribe` header + HTML unsubscribe link — STRONG positive

## Safe Alternatives

| Instead of | Use |
|-----------|-----|
| "FREE gift" | "Complimentary bonus" |
| "Act NOW" | "Reserve your spot" |
| "Buy today" | "Start your journey" |
| "Limited time" | "Available this season" |
| "Click here" | [Descriptive CTA text] |
| "Don't miss" | "Here's what's next" |
| "100% guaranteed" | "Backed by our promise" |
| "No obligation" | "Explore at your pace" |
| "Winner" | "You've earned" |
| "Exclusive deal" | "Member benefit" |
| "Congratulations" | "Great news" |
| "Urgent" | "Timely update" |

## SpamAssassin Content Rules
- `HTML_LINK_CLICK_HERE` — link text is "click here"
- `HTML_FONT_SIZE_TINY` — very small font size detected
- `HTML_FONT_LOW_CONTRAST` — text color too close to background
- `HTML_IMAGE_RATIO_02` — 0–20% text (mostly images)
- `HTML_IMAGE_ONLY_04` — 0–400 bytes text with images
- Excessive capitalization has specific scoring rules