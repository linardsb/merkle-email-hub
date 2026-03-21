# Plan: Fix Figma Design URL Connection Bug

## Context

Figma connections fail intermittently — the user reports the connection has broken 3 times. Root cause analysis reveals **two distinct bugs** that compound to make connections fragile:

### Bug 1: Figma URL format mismatch (URL regex too narrow)

The regex `_FIGMA_FILE_KEY_RE` at `app/design_sync/figma/service.py:29` only matches:
```
figma.com/design/<key>/...
figma.com/file/<key>/...
```

But Figma uses **many URL formats** depending on context:
- `figma.com/design/<key>/...` — current editor URL (matches ✅)
- `figma.com/file/<key>/...` — legacy URL (matches ✅)
- `figma.com/proto/<key>/...` — prototype link (fails ❌)
- `figma.com/board/<key>/...` — FigJam board (fails ❌)

More importantly, when a user copies a URL from the Figma browser tab, the URL may include **query parameters or fragments** like `?node-id=123:456&t=abc` — these don't break the regex but are worth noting.

The `list_files` method at line 110 constructs URLs as `https://www.figma.com/design/{file_key}` (no trailing slash, no title slug). The `extract_file_key` function then re-parses this URL. This round-trip works for the browse→select flow, but fails for **manual URL entry** with non-`/design/` or `/file/` paths.

**However**, the browse flow constructs clean URLs that match the regex. So Bug 1 alone doesn't explain "it worked before but breaks on reconnection." The intermittent failure points to Bug 2.

### Bug 2: Fernet token decryption fails after JWT secret rotation (the real intermittent failure)

In `app/design_sync/crypto.py`, the Fernet key is derived from:
```python
source = settings.design_sync.encryption_key or settings.auth.jwt_secret_key
```

If `design_sync.encryption_key` is empty (the default), the JWT secret is used. **If the JWT secret changes** (e.g., env var reloaded, container restart with different secret, or switching between dev environments), all previously encrypted tokens become **permanently undecryptable**. The `decrypt_token()` call in `sync_connection()` (line 245) will raise `InvalidToken`, which gets caught by the generic `except Exception` at line 257 and turned into:
- Status set to `"error"` with message `"Sync failed"`
- A `SyncFailedError("Token sync failed")` raised to the user

This explains why the connection **worked initially** but **fails on subsequent syncs/reconnections** — the encryption key drifted.

### Bug 3: No duplicate connection guard

`create_connection` in `service.py` doesn't check if a connection with the same `file_ref` + `provider` already exists. The user can create duplicate connections to the same file, leading to confusion when one works and the other doesn't (stale encrypted token).

## Files to Create/Modify

- `app/design_sync/figma/service.py` — Expand `_FIGMA_FILE_KEY_RE` to accept all Figma URL path types
- `app/design_sync/crypto.py` — Add `can_decrypt()` health-check function; improve error message on decrypt failure
- `app/design_sync/service.py` — Add token re-encryption on sync, add duplicate connection guard, improve error messages
- `app/design_sync/exceptions.py` — Add `TokenDecryptionError` for clearer error reporting
- `app/design_sync/schemas.py` — Add `ConnectionUpdateTokenRequest` schema for token refresh endpoint
- `app/design_sync/routes.py` — Add PATCH endpoint for token refresh
- `app/design_sync/repository.py` — Add `get_connection_by_file_ref()` and `update_connection_token()` methods
- `app/design_sync/tests/test_service.py` — Add tests for new URL formats, token refresh, duplicate guard
- `app/design_sync/tests/test_routes.py` — Add test for token refresh endpoint

## Implementation Steps

### Step 1: Expand Figma URL regex (`app/design_sync/figma/service.py`)

```python
# Line 29 — replace the regex to accept all Figma URL path types
_FIGMA_FILE_KEY_RE = re.compile(
    r"figma\.com/(?:design|file|proto|board|embed)/([a-zA-Z0-9]+)"
)
```

Also update the error message in `extract_file_key` (line 60):
```python
raise SyncFailedError(
    "Invalid Figma URL. Expected format: figma.com/design/<file_key>/... "
    "(also accepts /file/, /proto/, /board/, /embed/ paths)"
)
```

### Step 2: Add `TokenDecryptionError` (`app/design_sync/exceptions.py`)

```python
class TokenDecryptionError(AppError):
    """Raised when a stored access token cannot be decrypted (key rotation)."""
```

### Step 3: Improve crypto module (`app/design_sync/crypto.py`)

Add a `can_decrypt` health-check function:
```python
def can_decrypt(ciphertext: str) -> bool:
    """Check if a ciphertext can be decrypted with the current key."""
    try:
        _get_fernet().decrypt(ciphertext.encode())
        return True
    except Exception:
        return False
```

### Step 4: Add repository methods (`app/design_sync/repository.py`)

Add `get_connection_by_file_ref`:
```python
async def get_connection_by_file_ref(
    self, provider: str, file_ref: str
) -> DesignConnection | None:
    """Find an existing connection by provider + file reference."""
    result = await self._db.execute(
        select(DesignConnection).where(
            DesignConnection.provider == provider,
            DesignConnection.file_ref == file_ref,
        )
    )
    return result.scalar_one_or_none()
```

Add `update_connection_token`:
```python
async def update_connection_token(
    self,
    connection: DesignConnection,
    encrypted_token: str,
    token_last4: str,
) -> None:
    """Update the stored access token for a connection."""
    connection.encrypted_token = encrypted_token
    connection.token_last4 = token_last4
    await self._db.flush()
```

### Step 5: Add token refresh schema (`app/design_sync/schemas.py`)

```python
class ConnectionUpdateTokenRequest(BaseModel):
    """Request to update the access token on an existing connection."""

    connection_id: int
    access_token: str = Field(..., min_length=1, description="New provider access token / PAT")
```

### Step 6: Fix service layer (`app/design_sync/service.py`)

**6a.** In `create_connection`, add duplicate guard before creating:
```python
# After file_ref extraction, before validate_connection:
existing = await self._repo.get_connection_by_file_ref(provider_name, file_ref)
if existing is not None:
    raise ConflictError(
        f"A connection to this file already exists ('{existing.name}', id={existing.id}). "
        "Use the token refresh endpoint to update credentials."
    )
```

**6b.** In `sync_connection`, catch `TokenDecryptionError` specifically and set a descriptive error:
```python
try:
    access_token = decrypt_token(conn.encrypted_token)
except Exception as exc:
    await self._repo.update_status(
        conn, "error",
        error_message="Access token expired or encryption key changed. Please refresh your token."
    )
    raise TokenDecryptionError(
        "Cannot decrypt stored access token. The encryption key may have changed. "
        "Please update your access token via the connection settings."
    ) from exc
```

Move this decrypt call **before** the provider sync call, so the error is caught early.

**6c.** Add `refresh_token` method:
```python
async def refresh_token(
    self, connection_id: int, new_access_token: str, user: User
) -> ConnectionResponse:
    """Update the access token for an existing connection."""
    conn = await self._repo.get_connection(connection_id)
    if conn is None:
        raise ConnectionNotFoundError(f"Connection {connection_id} not found")
    if conn.project_id is not None:
        await self._verify_access(conn.project_id, user)

    # Validate new token with provider
    provider = self._get_provider(conn.provider)
    try:
        await provider.validate_connection(conn.file_ref, new_access_token)
    except SyncFailedError:
        raise
    except Exception as exc:
        raise SyncFailedError("Failed to validate new token") from exc

    # Re-encrypt and save
    encrypted = encrypt_token(new_access_token)
    token_last4 = new_access_token[-4:] if len(new_access_token) >= 4 else new_access_token
    await self._repo.update_connection_token(conn, encrypted, token_last4)
    await self._repo.update_status(conn, "connected")

    logger.info(
        "design_sync.token_refreshed",
        connection_id=connection_id,
        provider=conn.provider,
    )

    project_name = await self._get_project_name(conn.project_id)
    return ConnectionResponse.from_model(conn, project_name=project_name)
```

### Step 7: Add token refresh route (`app/design_sync/routes.py`)

```python
@router.patch("/connections/{connection_id}/token")
@limiter.limit("10/minute")
async def refresh_connection_token(
    connection_id: int,
    request: Request,
    data: ConnectionUpdateTokenRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ConnectionResponse:
    """Refresh the access token for a design connection."""
    return await service.refresh_token(connection_id, data.access_token, current_user)
```

### Step 8: Add tests

**8a.** `app/design_sync/tests/test_service.py` — new test cases:
- `test_extract_file_key_proto_url` — verifies `figma.com/proto/<key>/...` works
- `test_extract_file_key_board_url` — verifies `figma.com/board/<key>/...` works
- `test_create_connection_duplicate_raises_conflict` — duplicate file_ref blocked
- `test_sync_connection_token_decrypt_failure` — descriptive error on bad decrypt
- `test_refresh_token_success` — happy path for token refresh

**8b.** `app/design_sync/tests/test_routes.py` — new test case:
- `test_refresh_connection_token` — PATCH endpoint returns updated connection

## Security Checklist (scoped to this feature's endpoints)
- [x] Auth dependency — new PATCH route uses `require_role("developer")`
- [x] Authorization check — `refresh_token` calls `_verify_access()` for project-scoped connections
- [x] Rate limiting — `@limiter.limit("10/minute")` on new endpoint
- [x] Input validation — `ConnectionUpdateTokenRequest` uses Pydantic with `min_length=1`
- [x] Error responses use `AppError` hierarchy — new `TokenDecryptionError(AppError)`, existing `ConflictError`, `SyncFailedError`
- [x] No secrets in logs — token_last4 only, no full token logged

## Verification
- [ ] `make check` passes (includes lint, types, tests, frontend, security-check)
- [ ] New PATCH endpoint has auth + rate limiting
- [ ] Error responses don't leak internal types
- [ ] Existing tests for `extract_file_key` with `/design/` and `/file/` still pass
- [ ] New URL formats (`/proto/`, `/board/`, `/embed/`) are extracted correctly
- [ ] Token refresh flow: create connection → rotate JWT secret → refresh token → sync works
