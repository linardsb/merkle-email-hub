# Frontend SDK Regeneration

The TypeScript SDK in `cms/packages/sdk/` is generated from the backend's OpenAPI
schema via [`@hey-api/openapi-ts`](https://heyapi.dev/). The generated artefacts
(`openapi.json`, `src/client/types.gen.ts`, `src/client/sdk.gen.ts`) are
committed to the repo so the frontend has stable types without booting the
backend at install time.

## When to regenerate

Regenerate after any change that affects the wire format:

- New, renamed, or removed FastAPI route
- Added or removed Pydantic model field, type narrowing, or new schema
- Changed query/path/body parameter or response status code
- New router conditionally mounted by a feature flag (set the flag in
  `scripts/export-openapi.py` or in the CI job's `env:` block, otherwise
  the route disappears from the snapshot)

## How to regenerate

From repo root, with the backend's Python deps installed (`uv sync`):

```bash
make sdk-snapshot   # exports app/openapi.json -> cms/packages/sdk/openapi.json
make sdk-local      # runs openapi-ts to regenerate types.gen.ts + sdk.gen.ts
```

Or, with a running backend on `:8891`:

```bash
cd cms && pnpm --filter @email-hub/sdk generate-sdk:fetch
```

Stage and commit the resulting diff in `cms/packages/sdk/`.

## CI gate

The `sdk-check` job in `.github/workflows/ci.yml` runs `make sdk-check`, which:

1. Re-exports the OpenAPI snapshot from the current backend code.
2. Re-runs `openapi-ts` to regenerate the SDK artefacts.
3. `git diff --quiet cms/packages/sdk/` — fails the build if anything drifted.

A red `sdk-check` means the committed SDK is out of sync with the backend code.
Run the regen commands above locally and commit the result.

## Feature flags

Conditionally-mounted routers must have their flags enabled when the snapshot
is taken, otherwise CI will see a "missing routes" diff. Add the flag to:

- `scripts/export-openapi.py` (for local `make sdk-snapshot`)
- The `env:` block of the `sdk-check` job in `.github/workflows/ci.yml`

The credentials-health endpoint is the existing example (`CREDENTIALS__ENABLED`).
