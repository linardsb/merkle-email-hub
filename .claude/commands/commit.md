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
- Run a quick security lint on staged Python files (Bandit-level checks via ruff):
  ```bash
  git diff --cached --name-only --diff-filter=ACMR | grep '\.py$' | xargs -r uv run ruff check --select=S --no-fix
  ```
  If violations found, STOP and report them. Do not commit until resolved or user explicitly approves.
- For frontend changes, run quick pattern scan on staged `.ts`/`.tsx` files:
  ```bash
  git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(ts|tsx)$' | xargs -r grep -n 'dangerouslySetInnerHTML\|localStorage.*token\|localStorage.*auth\|eval('
  ```
  If violations found, WARN the user (soft gate — report but allow commit if user confirms).
- **Note:** These inline checks work even WITHOUT a pre-commit hook installed.

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

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `style`

**Scopes:** `qa-engine`, `agents`, `blueprints`, `knowledge`, `design-sync`, `connectors`, `components`, `auth`, `core`, `shared`, `cms`, or feature name

**Rules:**
- Subject line under 72 characters
- Imperative mood ("add feature" not "added feature")
- Body explains WHY, not WHAT (the diff shows what)

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
