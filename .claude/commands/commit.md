---
description: Stage files and create a conventional commit with safety checks
argument-hint: [file1] [file2] ... (optional, commits all changes if empty)
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*), Bash(git push:*), Bash(grep:*), Bash(xargs:*)
---

Review changes, scan for secrets, stage explicitly, and create a conventional commit.

# Commit — Conventional Git Commit

## INPUT

**Files to commit:** $ARGUMENTS (if empty, commit all changes)

## PROCESS

### 1. Review changes

```
!git status
```

```
!git diff --stat
```

```
!git log --oneline -5
```

### 2. Safety checks

- STOP if any of these files appear in the changes: `.env`, `*.pem`, `*.key`, `credentials.*`, `secrets.*`
- Warn the user and ask for confirmation before proceeding
- Run full lint on staged Python files (26 rule sets including security):
  ```bash
  git diff --cached --name-only --diff-filter=ACMR | grep '\.py$' | xargs -r uv run ruff check --no-fix
  ```
  If violations found, STOP and report them. Do not commit until resolved or user explicitly approves.
- Run security-specific lint separately to highlight Bandit findings:
  ```bash
  git diff --cached --name-only --diff-filter=ACMR | grep '\.py$' | xargs -r uv run ruff check --select=S --no-fix
  ```
- For frontend changes, run ESLint on staged files:
  ```bash
  git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(ts|tsx)$' | head -1 > /dev/null && cd cms && pnpm --filter web lint 2>/dev/null
  ```
  Also scan for high-risk patterns:
  ```bash
  git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(ts|tsx)$' | xargs -r grep -n 'dangerouslySetInnerHTML\|localStorage.*token\|localStorage.*auth\|eval('
  ```
  If violations found, WARN the user (soft gate — report but allow commit if user confirms).
- **Note:** These inline checks work even WITHOUT a pre-commit hook installed. With `make install-hooks`, pre-commit runs ruff format+lint, detect-secrets, and conventional commit validation automatically.

### 3. Stage files

If specific files were provided in $ARGUMENTS:
- Stage only those files: `git add [file1] [file2] ...`

If no files specified:
- Review all changes and stage appropriate files: `git add [specific files]`
- Do NOT use `git add -A` or `git add .` — always stage files explicitly

### 4. Create commit message

Use **conventional commit** format:

```
type(scope): short description

[optional body with more detail]

[optional Context: section — see below]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `style`

**Scopes:** `qa-engine`, `agents`, `blueprints`, `knowledge`, `design-sync`, `connectors`, `components`, `auth`, `core`, `shared`, `cms`, or feature name

**Rules:**
- Subject line under 72 characters
- Imperative mood ("add feature" not "added feature")
- Body explains WHY, not WHAT (the diff shows what)

### 4b. AI context tracking (if applicable)

If this commit includes changes to ANY of these AI context files, add a `Context:` section after the body:
- `.claude/commands/*.md` (slash commands)
- `.claude/rules/*.md` (path-triggered rules)
- `.claude/docs/*.md` (reference docs)
- `CLAUDE.md` (project instructions)

Format:
```
Context:
- commands: added /handoff for session continuity
- rules: updated testing.md with integration test patterns
- docs: created eval-system-guide.md reference doc
```

Only include this section when AI context files are part of the commit. Skip it for pure code changes.

### 5. Commit

Use HEREDOC format for the commit message:

```bash
git commit -m "$(cat <<'EOF'
type(scope): description

Optional body.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### 6. Push

Do NOT push automatically. Report that changes are committed locally. User can push with `git push` or include "and push" in arguments.

## OUTPUT

Report:
- Commit hash (short)
- Commit message used
- Files included
- Security check results (pass/warn/fail)
- Branch name
- Push status: local only (user can `git push` when ready)
