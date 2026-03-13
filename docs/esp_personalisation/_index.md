---
level: L4
type: index
domain: personalisation
qa_check: personalisation_syntax
version: "1.0"
---

# Email Personalisation Reference — Master Index

**Purpose:** Agent-facing index. Load this file first to identify which ESP file to load next.
**Coverage:** 7 ESPs — Braze, SFMC, Adobe Campaign, Klaviyo, Mailchimp, HubSpot, Iterable
**Format:** One file per ESP. Load only the file relevant to the task.

---

## FILE MAP

| File | ESP | Language | Delimiter |
|------|-----|----------|-----------|
| `esp_01_braze.md` | Braze | Liquid | `{{ }}` / `{% %}` |
| `esp_02_sfmc.md` | Salesforce Marketing Cloud | AMPscript | `%%[ ]%%` / `%%=Fn()=%%` |
| `esp_03_adobe_campaign.md` | Adobe Campaign Classic / v8 / Standard | JavaScript / EL | `<%= %>` / `<% %>` |
| `esp_04_klaviyo.md` | Klaviyo | Django Template Language | `{{ }}` / `{% %}` |
| `esp_05_mailchimp.md` | Mailchimp | Merge Language | `*|TAG|*` |
| `esp_06_hubspot.md` | HubSpot | HubL (Jinja2) | `{{ }}` / `{% %}` |
| `esp_07_iterable.md` | Iterable | Handlebars | `{{ }}` / `[[ ]]` |

---

## QUICK DISAMBIGUATION

**Liquid syntax `{{ }}` / `{% %}`** — used by Braze, Klaviyo, HubSpot
- Braze: `{{ ${first_name} }}` — dollar-sign-brace wrapping for standard attrs
- Klaviyo: `{{ first_name }}` — no wrapper; custom props via `{{ person|lookup:'Name' }}`
- HubSpot: `{{ contact.firstname }}` — dot-notation with object prefix

**AMPscript** — only SFMC uses this
- Code blocks: `%%[ VAR @var SET @var = value ]%%`
- Inline output: `%%=V(@var)=%%` or `%%=FunctionName()=%%`
- Personalization strings: `%%FNAME%%`

**EL / JavaScript `<%= %>`** — only Adobe Campaign uses this
- Output: `<%= recipient.firstName %>`
- Logic: `<% if (recipient.gender == 'M') { %>`

**Merge tags `*|TAG|*`** — only Mailchimp uses this

**Handlebars `{{ }}` / `[[ ]]`** — only Iterable uses this
- User/event data: `{{ }}` double curly
- Catalog/feed data: `[[ ]]` double square bracket

---

## SECTION CONTENTS BY FILE

### esp_01_braze.md
Standard attributes · Custom attributes · Event / API trigger properties · Campaign & Canvas metadata · Subscription state · Conditional logic · String filters · Number filters · Date filters · Array filters · assign & capture · For loops · Connected Content · Catalog lookups · Content Blocks · Abort logic · Random / A-B logic · Date arithmetic · Advanced patterns · Fallback patterns · Gotchas

### esp_02_sfmc.md
Personalization strings · Data Extension field references · Code block syntax · Inline output syntax · Conditional logic (IF/ELSEIF/ELSE) · String functions · Date functions · Math functions · DE Lookup functions · Loops (FOR…NEXT) · Dynamic content rules · Server-Side JavaScript (SSJS) · Complete function reference · Advanced patterns · Fallback patterns · Gotchas

### esp_03_adobe_campaign.md
Core syntax · Standard recipient fields · Personalisation blocks (pre-built) · JavaScript expressions · Conditional logic · Variables & calculated fields · Date formatting · String operations · Dynamic content · External file / data source · Delivery & campaign metadata · Classic vs Standard differences · Advanced patterns · Fallback patterns · Gotchas

### esp_04_klaviyo.md
Profile tags · Custom profile properties · Event variables · Organisation tags · Link & utility tags · Conditional logic · Filters · For loops & forloop variables · Common event schemas · Dynamic content blocks (visual editor) · Advanced patterns · Fallback patterns · Gotchas

### esp_05_mailchimp.md
Contact / subscriber tags · Audience & account tags · System & campaign tags · Date tags · Conditional merge tags (IF/ELSEIF/IFNOT) · Group-based conditionals · Automation email tags · RSS feed tags · Content encoding tags · Custom field tags · Transactional merge language · Transactional Handlebars · Advanced patterns · Fallback patterns · Gotchas

### esp_06_hubspot.md
Contact tokens · Company tokens · Deal tokens · Ticket tokens · Owner tokens · Office location tokens · Subscription & utility tokens · Conditional logic · Filters · Smart content rules · Advanced patterns · Fallback patterns · Finding internal property names · Gotchas

### esp_07_iterable.md
User profile fields · Special field name syntax · Built-in system variables · Event / trigger data · Conditional logic · Comparison helpers · String helpers · Date helpers · Number & math helpers · Array / list helpers · Loops (each) · Data feeds & catalog · Snippets · Skip send logic · Whitespace control · Advanced patterns · Fallback patterns · Gotchas

---

## CROSS-ESP QUICK REFERENCE

| Feature | Braze | SFMC | Adobe | Klaviyo | Mailchimp | HubSpot | Iterable |
|---------|-------|------|-------|---------|-----------|---------|----------|
| **Language** | Liquid | AMPscript | JS / EL | Django | Merge Tags | HubL | Handlebars |
| **First name** | `{{ ${first_name} }}` | `%%FirstName%%` | `<%= recipient.firstName %>` | `{{ first_name }}` | `*\|FNAME\|*` | `{{ contact.firstname }}` | `{{firstName}}` |
| **Default / fallback** | `\| default: 'x'` | `IIF(Empty(v),'x',v)` | `\|\| 'x'` in JS | `\|default:'x'` | IF/ELSE block | `\| default('x')` | `{{defaultIfEmpty v 'x'}}` |
| **Conditional** | `{% if %}{% endif %}` | `IF…ENDIF` | `<% if(){} %>` | `{% if %}{% endif %}` | `*\|IF:FIELD\|*…*\|END:IF\|*` | `{% if %}{% endif %}` | `{{#if}}{{/if}}` |
| **Loops** | `{% for item in arr %}` | `FOR @i = 1 TO n DO…NEXT` | `<% for(var i…) %>` | `{% for item in arr %}` | Not natively supported | Not natively supported | `{{#each arr}}{{/each}}` |
| **External data** | Connected Content | LookupRows / DE | FDA / JS fetch | Not native | Not native | Custom tokens (API) | Data Feeds / Catalog |
| **Reusable blocks** | Content Blocks | Content Builder | Personalisation Blocks | Not native | Content Studio | Smart modules | Snippets |
| **Abort / skip send** | `{% abort_message() %}` | Journey suppression | Journey action | Flow filter | Not available | Suppression list | `{{sendSkip cause=""}}` |
| **Case-sensitive** | Yes | No | Yes | Yes | Yes (tags) | No | Yes |
| **Custom properties** | `{{ custom_attribute.${name} }}` | `[ColumnName]` in DE | `<%= recipient.customField %>` | `{{ person\|lookup:'Name' }}` | `*\|CUSTOMTAG\|*` | `{{ contact.internal_name }}` | `{{profile.fieldName}}` |

---

## COMMON TASK ROUTING

| Task | Go to section in ESP file |
|------|--------------------------|
| Insert first name with fallback | Fallback Patterns |
| Show different content per loyalty tier | Conditional Logic |
| Loop through purchased products | Loops |
| Format a date field | Date Filters / Helpers |
| Fetch external API data | Connected Content (Braze) / SSJS (SFMC) / Data Feeds (Iterable) |
| Abort / suppress send | Abort Logic / Skip Send Logic |
| Reuse a content block | Content Blocks / Snippets / Personalisation Blocks |
| Build a dynamic image URL | Advanced Patterns |
| Create personalised subject line | Advanced Patterns |
| Debug empty / blank output | Gotchas & Debugging |

---

## QA Integration

All ESP reference files in this directory are L4 sources for the `personalisation_syntax` QA check (#11). The QA engine validates:

- **Platform detection** — Identifies which ESP syntax is present (Braze/SFMC/Adobe/Klaviyo/Mailchimp/HubSpot/Iterable)
- **Delimiter balance** — Ensures all platform-specific delimiters are properly opened and closed
- **Conditional balance** — Validates if/endif, IF/ENDIF, etc. are properly paired
- **Fallback completeness** — Flags output tags without default/fallback values
- **Syntax correctness** — Platform-specific syntax validation (Liquid filters, AMPscript functions, etc.)
- **Nesting depth** — Warns on conditionals nested > 3 levels deep
- **Mixed platform** — Flags templates mixing multiple ESP syntaxes

### Configuration

```yaml
personalisation_syntax:
  enabled: true
  severity: warning
  threshold: 0.5
  params:
    deduction_mixed_platform: 0.30
    deduction_delimiter_unbalanced: 0.15
    deduction_conditional_unbalanced: 0.15
    deduction_fallback_missing: 0.05
    deduction_syntax_error: 0.10
```

### Related Files

- Check implementation: `app/qa_engine/checks/personalisation_syntax.py`
- Validator: `app/qa_engine/personalisation_validator.py`
- YAML rules: `app/qa_engine/rules/personalisation_syntax.yaml`
- Custom checks: `app/qa_engine/custom_checks.py` (12 `personalisation_*` functions)
