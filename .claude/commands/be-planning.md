# Backend Planning — Create Implementation Plan

Research the codebase and create a self-contained implementation plan.

## Process

1. **Understand the task** — Read the user's requirements carefully
2. **Research existing code** — Only `Read` files you will list in "Files to Create/Modify".

   **jCodeMunch** (repo from `list_repos`):
   - `search_symbols(query, kind, file_pattern)` — find related functions/classes
   - `get_file_outline(file_path)` — understand file structure without reading
   - `get_symbol(symbol_name)` — read specific function/class code
   - `find_references(symbol_name)` — trace usage across codebase
   - `get_file_tree(path_prefix)` — discover feature layout

   **jDocMunch** (repo: `local/merkle-email-hub`):
   - `search_sections(query, doc_path)` → `get_section(section_id)` for CLAUDE.md architecture context and TODO.md task context
   - `get_document_outline(doc_path)` for smaller docs (<50 sections) when you need full structure

3. **Identify files to create/modify** — List every file that needs changes
4. **Write the plan** — Step-by-step instructions that another agent can follow

## Plan Format

Save the plan to `.agents/plans/{feature-name}.md` with this structure:

```markdown
# Plan: {Feature Name}

## Context
{Why this change is needed}

## Files to Create/Modify
- `app/{feature}/models.py` — {what changes}
- ...

## Implementation Steps
1. {Step with exact code or clear instructions}
2. ...

## Security Checklist
For every new/modified endpoint in this plan, address each item from the backend security checklist below.

## Verification
- [ ] `make check` passes (includes lint, types, tests, frontend, security-check)
- [ ] New endpoints have auth + rate limiting
- [ ] Error responses don't leak internal types
```

@_shared/backend-conventions.md
@_shared/backend-security-scoped.md
@_shared/python-anti-patterns.md
