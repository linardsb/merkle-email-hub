# Secret Rotation Procedures

Tracks every long-lived secret in the deployment, where it is stored, how to rotate it, expected downtime, and last-rotated date. Update the **Last rotated** column whenever a secret is replaced.

> Quarterly review owner: security ops. Open an issue tagged `security/rotation` if any row is older than 365 days.

## Index

| Secret | Storage | Owner | Procedure | Downtime | Last rotated |
|--------|---------|-------|-----------|----------|--------------|
| `POSTGRES_PASSWORD` | Coolify env, `.env` | Platform | [§DB password](#postgres_password) | ~30 s (rolling) | YYYY-MM-DD |
| `REDIS_PASSWORD` | Coolify env, `.env` | Platform | [§Redis password](#redis_password) | ~10 s | YYYY-MM-DD |
| `AUTH__JWT_SECRET_KEY` | Coolify env, `.env` | Backend | [§JWT secret](#auth__jwt_secret_key) | Forces re-login | YYYY-MM-DD |
| AES encryption key (`SECURITY__AES_KEY`) | Coolify env, `.env` | Backend | [§AES key](#aes-key) | Re-encryption window | YYYY-MM-DD |
| `AI__ANTHROPIC_API_KEY` | Coolify env, `.env` | AI | [§LLM API keys](#llm-api-keys) | None (rolling) | YYYY-MM-DD |
| `AI__OPENAI_API_KEY` | Coolify env, `.env` | AI | [§LLM API keys](#llm-api-keys) | None (rolling) | YYYY-MM-DD |
| `AUTH__DEMO_USER_PASSWORD` | Coolify env, `.env` | Backend | [§Demo password](#auth__demo_user_password) | None | YYYY-MM-DD |
| Figma webhook signing secret | Coolify env, `.env` | Design Sync | [§Figma webhook](#figma-webhook-secret) | None | YYYY-MM-DD |
| ESP credentials (Braze / SFMC / Adobe / Taxi) | DB `connectors.credentials` (encrypted) | Connectors | [§ESP credentials](#esp-credentials) | Per-connector | YYYY-MM-DD |
| Sentry DSN (`SENTRY__DSN`) | Coolify env | Platform | [§Sentry DSN](#sentry-dsn) | None | YYYY-MM-DD |

## POSTGRES_PASSWORD

1. Generate: `openssl rand -base64 36 | tr -d '/+=' | head -c 32`
2. Update Coolify env (`POSTGRES_PASSWORD`).
3. Update DB user inside the running container:
   `docker compose exec db psql -U postgres -c "ALTER USER postgres WITH PASSWORD '<new>'"`
4. Trigger Coolify redeploy of `app` service so new env propagates.
5. Verify `app/health/db` returns 200.
6. Update `Last rotated` here.

## REDIS_PASSWORD

1. Generate: `openssl rand -base64 36 | tr -d '/+='`
2. Update Coolify env (`REDIS_PASSWORD`).
3. Coolify redeploys `redis` and `app` together; confirm `redis-cli -a <new> ping` returns `PONG`.
4. Update `Last rotated`.

## AUTH__JWT_SECRET_KEY

> All issued JWTs become invalid immediately. Users must re-authenticate.

1. Generate: `openssl rand -base64 48 | tr -d '/+='`
2. Update Coolify env (`AUTH__JWT_SECRET_KEY`); minimum 32 chars (enforced by `Field(min_length=32)`).
3. Production sentinel rejects defaults — verify env starts with anything except `CHANGE-ME-IN-PRODUCTION`.
4. Coolify redeploys `app`. Existing sessions return 401; users re-login.
5. Update `Last rotated`.

> **Grace-period rotation** (verifying tokens signed by old + new keys for a window) is not implemented. If a zero-downtime rotation is needed, that change is its own plan.

## AES key

The AES key encrypts ESP credentials in `connectors.credentials.ciphertext`. Rotation requires re-encrypting every row.

1. Generate new key: `openssl rand -base64 32`
2. Add as `SECURITY__AES_KEY_NEW` (do **not** replace `SECURITY__AES_KEY` yet).
3. Run `uv run python -m app.connectors.scripts.rotate_aes_key` (script reads old key from `SECURITY__AES_KEY`, writes ciphertext re-encrypted under `SECURITY__AES_KEY_NEW`).
4. Once script reports 100 % migration: swap envs (`SECURITY__AES_KEY` ← new value, drop `_NEW`).
5. Coolify redeploy.
6. Update `Last rotated`.

> The rotation script does not yet exist; this row is the authoritative spec for it. Track in `docs/dependency-debt.md` until implemented.

## LLM API keys

Anthropic and OpenAI keys are read by `app/ai/adapters/`. Rotation is rolling because both providers support multiple active keys per workspace.

1. In the provider console, create a **new** key — keep the old key live.
2. Update Coolify env with the new key.
3. Coolify redeploys `app`.
4. After 30 minutes (allow in-flight requests to drain), revoke the old key in the provider console.
5. Update `Last rotated`.

> Credential pool (Phase 46.1) supports multiple keys per provider; for production, use the pool with N≥2 keys to keep rotation zero-disruption. See `app/core/credentials.py`.

## AUTH__DEMO_USER_PASSWORD

Only relevant in dev/staging. Production sentinel (`Settings._validate_production_secrets`) refuses `"admin"`. Rotate as needed.

## Figma webhook secret

Set in Figma's webhook console; receiver validates HMAC in `app/design_sync/webhook.py`.

1. Generate: `openssl rand -hex 32`
2. Update **both** Coolify env (`DESIGN_SYNC__FIGMA_WEBHOOK_SECRET`) and Figma webhook config in the same change window.
3. Verify by triggering a Figma file save; check `design_sync.webhook_received` log line.
4. Update `Last rotated`.

## ESP credentials

Per-project, stored encrypted in `connectors.credentials`. Customer-supplied — rotation is initiated by the customer or by the connector pool's cooldown logic on 401/403.

1. Customer regenerates key in ESP console.
2. Customer pastes into `/connectors/{id}/credentials` UI.
3. `CredentialsService.update()` re-encrypts under current AES key.
4. Old credential is purged from DB; pool cooldown clears on next successful call.

## Sentry DSN

Read-only sink — rotation needed only if compromised.

1. In Sentry project settings → Client Keys, regenerate DSN.
2. Update Coolify env (`SENTRY__DSN`).
3. Coolify redeploy. Frontend DSN (Next.js) rotates separately via `NEXT_PUBLIC_SENTRY_DSN`.
4. Update `Last rotated`.

## Full-history secret-leak scan

Run **once** to baseline; then trust pre-commit `detect-secrets` going forward.

```sh
uv run detect-secrets scan --all-files \
  --baseline .secrets.baseline.full-history.json
```

Triage findings:
- False positive → mark as `is_secret: false` in baseline.
- Real leak → rotate that secret using the procedure above, then optionally redact via `git filter-repo` (separate, gated decision).

## Quarterly review checklist

- [ ] Every row has a `Last rotated` date within the last 365 days (or has a documented exception).
- [ ] LLM API keys rotated at least annually.
- [ ] Production sentinel still trips on `"CHANGE-ME-IN-PRODUCTION"` — confirm with `uv run pytest app/core/tests/test_config_security.py`.
- [ ] `docs/security/secret-rotation.md` index matches actual env vars in `docker-compose.yml` (every `${VAR:?...}` has a row).
