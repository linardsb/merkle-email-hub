# Eval Human Labeling Checklist

**540 rows total** across 3 agents. For each row, open the trace file,
review the agent output, then set `human_pass` to `true` or `false`.

Files to edit:
- `traces/scaffolder_human_labels.jsonl` (180 rows)
- `traces/dark_mode_human_labels.jsonl` (150 rows)
- `traces/content_human_labels.jsonl` (210 rows)

When done: `make eval-calibrate && make eval-qa-calibrate`
Targets: TPR >= 0.85, TNR >= 0.80 per judge criterion; QA agreement >= 75%.

---

## Scaffolder (180 rows)

### scaff-001

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ❌) → human_pass: ___
- [ ] `mso_conditionals` (judge said ✅) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-002

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ❌) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-003

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ❌) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-004

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ✅) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-005

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ❌) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ✅) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-006

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ❌) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ✅) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-007

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ❌) → human_pass: ___
- [ ] `mso_conditionals` (judge said ✅) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-008

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ❌) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-009

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ✅) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-010

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ✅) → human_pass: ___
- [ ] `table_structure` (judge said ❌) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-011

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ❌) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### scaff-012

**Judge criteria:**
- [ ] `brief_fidelity` (judge said ✅) → human_pass: ___
- [ ] `email_layout` (judge said ✅) → human_pass: ___
- [ ] `mso_conditionals` (judge said ❌) → human_pass: ___
- [ ] `table_structure` (judge said ✅) → human_pass: ___
- [ ] `code_quality` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

## Dark Mode (150 rows)

### dark-001

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ✅) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-002

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ✅) → human_pass: ___
- [ ] `outlook_selectors` (judge said ❌) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-003

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ❌) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-004

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ✅) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-005

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ❌) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-006

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ✅) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-007

**Judge criteria:**
- [ ] `color_coherence` (judge said ❌) → human_pass: ___
- [ ] `html_preservation` (judge said ✅) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-008

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ✅) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-009

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ✅) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### dark-010

**Judge criteria:**
- [ ] `color_coherence` (judge said ✅) → human_pass: ___
- [ ] `html_preservation` (judge said ❌) → human_pass: ___
- [ ] `outlook_selectors` (judge said ✅) → human_pass: ___
- [ ] `media_query` (judge said ✅) → human_pass: ___
- [ ] `meta_tags` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

## Content (210 rows)

### content-001

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-002

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ❌) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-003

**Judge criteria:**
- [ ] `copy_quality` (judge said ❌) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-004

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ❌) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-005

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ❌) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-006

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ❌) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-007

**Judge criteria:**
- [ ] `copy_quality` (judge said ❌) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-008

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ❌) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-009

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ❌) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-010

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-011

**Judge criteria:**
- [ ] `copy_quality` (judge said ❌) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-012

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ❌) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-013

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ✅) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ❌) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

### content-014

**Judge criteria:**
- [ ] `copy_quality` (judge said ✅) → human_pass: ___
- [ ] `tone_match` (judge said ❌) → human_pass: ___
- [ ] `spam_avoidance` (judge said ✅) → human_pass: ___
- [ ] `length_appropriate` (judge said ✅) → human_pass: ___
- [ ] `grammar` (judge said ✅) → human_pass: ___
**QA checks:**
- [ ] `html_validation` (judge: —) → human_pass: ___
- [ ] `css_support` (judge: —) → human_pass: ___
- [ ] `file_size` (judge: —) → human_pass: ___
- [ ] `link_validation` (judge: —) → human_pass: ___
- [ ] `spam_score` (judge: —) → human_pass: ___
- [ ] `dark_mode` (judge: —) → human_pass: ___
- [ ] `accessibility` (judge: —) → human_pass: ___
- [ ] `fallback` (judge: —) → human_pass: ___
- [ ] `image_optimization` (judge: —) → human_pass: ___
- [ ] `brand_compliance` (judge: —) → human_pass: ___

---
**Total: 540 rows**
