# Copy Quality Boundaries — Judge Reference

## Pass/Fail Calibration

The judge evaluates **correctness and appropriateness**, not **creativity or marketing effectiveness**. Copy that is functional, clear, and meets the brief requirements is a PASS — even if a human copywriter could improve it.

## PASS Criteria (All Must Be True)

- Grammatically correct (no spelling errors, proper punctuation)
- Matches the requested tone (professional/casual/urgent/friendly as specified)
- No spam trigger words or phrases (FREE!!!, Act Now!!!, Limited Time)
- Addresses the brief's requirements (subject line length, CTA text, content focus)
- No PII leakage (placeholder tokens like `{{ first_name }}` are fine; hardcoded emails/phones are not)
- Factually consistent (doesn't contradict the brief or other generated content)

## FAIL Criteria (Any One Triggers Failure)

- Grammatical errors or typos
- Tone mismatch (casual when professional was requested, or vice versa)
- Contains known spam triggers that would affect deliverability
- Missing key elements specified in the brief
- Contains placeholder text that wasn't replaced (e.g., `[INSERT NAME HERE]`)
- Exceeds specified length constraints

## Boundary Cases (Default to PASS)

- **Generic but correct**: "Shop our latest collection" — not compelling, but grammatically correct and appropriate. **PASS**
- **Slightly verbose**: A subject line at 58 characters when 50 was ideal but 60 was the hard limit. **PASS**
- **Conservative tone**: Copy that's professional but not exciting when "engaging" was requested — if it's not actively boring or inappropriate. **PASS**
- **Repetitive structure**: Multiple CTAs using similar phrasing ("Shop Now", "Browse Now", "Discover Now"). Repetitive but not incorrect. **PASS**

## Boundary Cases (Default to FAIL)

- **Tone violation**: Using exclamation marks and casual language when "formal corporate" was requested. **FAIL**
- **Off-brand vocabulary**: Using slang or colloquialisms for a luxury brand. **FAIL**
- **Misleading urgency**: Adding "Last chance!" or countdown language not mentioned in the brief. **FAIL**
