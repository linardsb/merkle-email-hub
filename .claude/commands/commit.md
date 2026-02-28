# Commit — Stage and Commit with Safety Checks

Create a conventional commit with safety checks.

## Process

1. **Check for secrets** — Scan staged files for API keys, passwords, tokens
2. **Review changes** — `git diff --cached` to understand what's being committed
3. **Generate commit message** — Follow conventional commits format:
   - `feat:` — New feature
   - `fix:` — Bug fix
   - `refactor:` — Code restructuring
   - `chore:` — Maintenance
   - `docs:` — Documentation
   - `test:` — Tests
4. **Commit** — Create the commit

## Rules
- Never commit `.env`, credentials, or API keys
- Keep commit messages concise (under 72 chars for first line)
- Use present tense ("add feature" not "added feature")
