# Training Figma Links & Screenshots

## Asset Layout

Each snapshot case has **self-contained** assets in `data/debug/{case_id}/assets/`.
Runtime image downloads go to `data/design-assets/{connection_id}/` (ephemeral cache, gitignored).

| Case ID | Campaign | Assets dir | Images | Source |
|---------|----------|-----------|--------|--------|
| 5 | MAAP x KASK | `data/debug/5/assets/` | 98 | Figma node 2833-1623 children |
| 6 | Starbucks Pumpkin Spice | `data/debug/6/assets/` | 21 | Figma node 2833-1424 children |
| 10 | Mammut Duvet Day | `data/debug/10/assets/` | 38 | Figma node 2833-1135 children |

To re-export case assets from Figma, provide the URL with the frame `node-id` parameter.
The pipeline scopes to that frame via `_filter_structure(selected_node_ids=["<node-id>"])`.

---

## Figma Links

### mammut-duvet-day.html
- **Case ID:** 10
- **Node ID:** 2833-1135
- **Local HTML:** `email-templates/training_HTML/for_converter_engine/mammut-duvet-day.html`
- **Assets:** `data/debug/10/assets/` (38 images)
- **Figma:** https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1135&t=3jOOAQkN52tU2ty8-0

### starbucks-pumpkin-spice.html
- **Case ID:** 6
- **Node ID:** 2833-1424
- **Local HTML:** `email-templates/training_HTML/for_converter_engine/starbucks-pumpkin-spice.html`
- **Assets:** `data/debug/6/assets/` (21 images)
- **Figma:** https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1424&t=3jOOAQkN52tU2ty8-0

### maap-kask.html
- **Case ID:** 5
- **Node ID:** 2833-1623
- **Local HTML:** `email-templates/training_HTML/for_converter_engine/maap-kask.html`
- **Assets:** `data/debug/5/assets/` (98 images)
- **Figma:** https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1623&t=3jOOAQkN52tU2ty8-0
