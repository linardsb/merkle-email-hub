# Tech Debt 04 — Connector Deduplication

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** Two pairs of byte-equivalent ESP connector services collapsed into ABCs. Removes ~400 LOC, fixes 4 production MagicMock guards, narrows exception handling.
**Goal:** One OAuth ABC + one API-key ABC; per-vendor subclasses are ~30 LOC each.
**Estimated effort:** ½ day, single PR.
**Prerequisite:** Plan 01 landed (F022/F023 are touched there for narrowing only — this plan replaces those sites entirely).

## Findings addressed

F020 (SFMC ≈ Adobe OAuth duplication) — Critical
F021 (Braze ≈ Taxi API-key duplication) — Critical
F022 (production MagicMock guards) — High (re-fixed by this refactor)
F023 (KeyError counts as transport failure) — High (re-fixed)
F024 (unbounded ClassVar `_token_cache`) — High (re-fixed)
F069 (truncated cache key collision risk) — Medium (re-fixed)

## Pre-flight

```bash
git checkout -b refactor/tech-debt-04-connector-abcs
make check
# Verify the four services have no in-flight uncommitted changes:
git diff app/connectors/{braze,sfmc,adobe,taxi}/
```

## Part A — `ApiKeyConnectorService` ABC (Braze + Taxi)

### A1. Create the base

**New file:** `app/connectors/_base/api_key.py`:

```python
from abc import ABC, abstractmethod
from typing import Any
import httpx
import json

from app.connectors.exceptions import ExportFailedError
from app.core.credentials import CredentialPool, NoHealthyCredentialsError
from app.core.config import get_settings

class ApiKeyConnectorService(ABC):
    def __init__(self, *, pool: CredentialPool | None = None) -> None:
        self._pool = pool or get_settings().credentials.pools.get(self.service_name)

    @property
    @abstractmethod
    def service_name(self) -> str: ...

    @abstractmethod
    def _endpoint(self, *, asset_name: str) -> str: ...

    @abstractmethod
    def _auth_header(self, api_key: str) -> dict[str, str]: ...

    @abstractmethod
    def _build_payload(self, *, html: str, name: str, **kwargs: Any) -> dict[str, Any]: ...

    @abstractmethod
    def _external_id_from_response(self, body: dict[str, Any]) -> str: ...

    @abstractmethod
    def _mock_external_id(self, name: str) -> str: ...
    """Stub id returned when no credentials and no pool are available — preserves existing behaviour."""

    async def _lease_credentials(
        self, credentials: dict[str, str] | None
    ) -> tuple[str, "CredentialLease | None"]:
        # Caller-supplied credentials take precedence over pool. Returns (api_key, lease|None).
        if credentials:
            return self._extract_key(credentials), None
        try:
            lease = await self._pool.acquire()
        except NoHealthyCredentialsError as exc:
            raise ExportFailedError("no healthy credentials") from exc
        return lease.key, lease

    @abstractmethod
    def _extract_key(self, credentials: dict[str, str]) -> str: ...

    async def export(
        self, html: str, name: str, credentials: dict[str, str] | None = None
    ) -> str:
        # Preserve existing API: positional (html, name, credentials), credentials optional.
        # When both credentials and pool are absent, return a deterministic mock id.
        if credentials is None and self._pool is None:
            return self._mock_external_id(name)
        api_key, lease = await self._lease_credentials(credentials)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    self._endpoint(asset_name=name),
                    json=self._build_payload(html=html, name=name),
                    headers=self._auth_header(api_key),
                )
                resp.raise_for_status()
                lease.report_success()
                return self._external_id_from_response(resp.json())
        except (httpx.RequestError, json.JSONDecodeError) as exc:
            if lease: lease.report_failure(0)
            raise ExportFailedError(f"transport: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            if lease: lease.report_failure(exc.response.status_code)
            raise ExportFailedError(f"http {exc.response.status_code}") from exc
        # KeyError, TypeError on response parsing → propagate without lease blame
```

**API contract preservation:** The ABC keeps the existing `(html, name, credentials=None)` positional signature so production callers in `app/connectors/service.py:269,324` and existing tests don't move. Subclasses **delete** their `package_content_block` / `package_content_area` / `package_delivery_fragment` / `package_template` helpers — they were only used internally by the old `export()`. The four `test_package_*` methods in `app/connectors/tests/test_service.py` are removed in this plan (preflight already removed them).

### A2. Migrate `BrazeConnectorService`

`app/connectors/braze/service.py:18-98` — replace with:

```python
class BrazeConnectorService(ApiKeyConnectorService):
    service_name = "braze"

    def _endpoint(self, *, asset_name: str) -> str:
        return f"{settings.braze.api_url}/content_blocks/info"

    def _auth_header(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    def _extract_key(self, credentials: dict[str, str]) -> str:
        return credentials["api_key"]

    def _build_payload(self, *, html: str, name: str) -> dict[str, Any]:
        return {"name": name, "content": html, "tags": ["email-hub"]}

    def _external_id_from_response(self, body):
        return body["content_block_id"]

    def _mock_external_id(self, name: str) -> str:
        return f"braze_cb_{name.lower().replace(' ', '_')}"
```

Keep MagicMock guard fix from Plan 01 fold into the typed `__init__`. Delete the old service body.

### A3. Migrate `TaxiConnectorService`

Same pattern. Header is `X-API-Key`; payload includes `syntax_version`. ~30 LOC.

### A4. Remove `_lease_credentials` MagicMock guards

The base's `__init__` accepts an explicit `pool` so tests can inject `MagicMock()` directly. **Update `app/connectors/tests/conftest.py`** to provide a typed fake pool.

## Part B — `OAuthConnectorService` ABC (SFMC + Adobe)

### B1. Create the base

**New file:** `app/connectors/_base/oauth.py`:

```python
from collections import OrderedDict
from app.core.cache import LruWithTtl  # new helper, see B4

class OAuthConnectorService(ApiKeyConnectorService):
    """OAuth client-credentials flow + 401-retry-once cache eviction."""

    _token_cache: LruWithTtl[str, tuple[str, float]]  # instance, not ClassVar

    def __init__(self, *, pool=None) -> None:
        super().__init__(pool=pool)
        self._token_cache = LruWithTtl(maxsize=64, default_ttl=3600)

    @abstractmethod
    def _token_url(self) -> str: ...

    @abstractmethod
    def _asset_url(self) -> str: ...

    def _cache_key(self, client_id: str) -> str:
        return f"{self.service_name}:{client_id}"  # no truncation; addresses F069

    async def _get_access_token(self, client_id: str, client_secret: str) -> str:
        key = self._cache_key(client_id)
        if cached := self._token_cache.get(key):
            return cached

        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(self._token_url(), data={
                "grant_type": "client_credentials",
                "client_id": client_id, "client_secret": client_secret,
            })
            resp.raise_for_status()
            tok = resp.json()["access_token"]
            ttl = resp.json().get("expires_in", 3600) - 60
            self._token_cache.put(key, tok, ttl=ttl)
            return tok

    async def _lease_credentials(self):
        # validate JSON shape: {client_id, client_secret}
        ...

    # override export() to handle 401 → cache evict + retry once
```

### B2. Migrate SFMC and Adobe

`app/connectors/sfmc/service.py:23-158` and `adobe/service.py:23-161` — collapse to ~30-40 LOC each. Differences:
- `_token_url()`: SFMC's `auth.sfmc.…/v2/token`; Adobe's `ims-na1.adobelogin.com/ims/token/v3`.
- `_asset_url()`: SFMC `…/asset/v1/content/assets`; Adobe `…/cm/asset/v1/upload`.
- `_build_payload()`: SFMC uses `name`; Adobe uses `label`.
- `_external_id_from_response()`: SFMC `id`; Adobe `PKey`.

### B3. Drop the `ClassVar` token cache

Remove `_token_cache: ClassVar[dict]` from both subclasses. The base's instance attribute replaces it. Process-wide leakage and unbounded growth (F024) is fixed by `LruWithTtl(maxsize=64)`.

### B4. Add `LruWithTtl` helper

**New file:** `app/core/cache.py`:
```python
from collections import OrderedDict
import time

class LruWithTtl[K, V]:
    def __init__(self, *, maxsize: int, default_ttl: float):
        self._d: OrderedDict[K, tuple[V, float]] = OrderedDict()
        self._maxsize = maxsize
        self._default_ttl = default_ttl

    def get(self, key: K) -> V | None:
        item = self._d.get(key)
        if item is None: return None
        value, expires_at = item
        if expires_at < time.monotonic():
            del self._d[key]; return None
        self._d.move_to_end(key)
        return value

    def put(self, key: K, value: V, *, ttl: float | None = None) -> None:
        if key in self._d: del self._d[key]
        self._d[key] = (value, time.monotonic() + (ttl or self._default_ttl))
        if len(self._d) > self._maxsize:
            self._d.popitem(last=False)
```

10 LOC, testable in isolation.

## Part C — Tests

Add per-service tests for the four connectors. **New files:**
- `app/connectors/tests/test_braze_service.py`
- `app/connectors/tests/test_sfmc_service.py`
- `app/connectors/tests/test_adobe_service.py`
- `app/connectors/tests/test_taxi_service.py`

Coverage matrix per service:
- 200 happy path → returns external id.
- 401 → token cache evicted, retried once (OAuth only).
- 429 → `ExportFailedError`.
- Malformed JSON in response → `ExportFailedError`, lease.report_failure(0).
- `KeyError` on response parse → `ExportFailedError`, lease NOT blamed (this is the F023 fix).
- `NoHealthyCredentialsError` → `ExportFailedError("no healthy credentials")`.

This addresses audit F066 (no per-service tests).

## Verification

```bash
make check
pytest app/connectors/ -v
# Confirm zero remaining ClassVar token cache:
rg "_token_cache: ClassVar" app/connectors/
# Confirm zero MagicMock isinstance guards:
rg "isinstance.*\.pools.*dict" app/connectors/
```

## Rollback

Single PR revert. ABCs are net-new files; subclass code is a delete-and-replace.

## Risk notes

- **Test fixture migration is the highest-risk step.** Many existing tests rely on `_token_cache` being class-shared (state leaks across tests intentionally to verify caching). After the move, each test gets a fresh instance — explicit caching tests must construct a single service and call twice.
- **Authentication shape parity**: SFMC/Adobe `_lease_credentials` does `json.loads` + dict-shape validation. Preserve in the OAuth base; raise typed error on bad shape.
- **Don't merge with Plan 01.** Plan 01 narrows exception handling at the existing call sites; Plan 04 replaces those sites entirely. If Plan 01 hasn't landed, skip its connector items (F022, F023) and let this plan supersede them.

## Done when

- [ ] `app/connectors/_base/{api_key,oauth}.py` exist with full test coverage.
- [ ] All 4 vendor services ≤ 50 LOC.
- [ ] `app/core/cache.py:LruWithTtl` exists with unit tests.
- [ ] Per-service tests cover the 6 cases above.
- [ ] No `ClassVar` token cache remaining.
- [ ] `make check` green.
- [ ] PR titled `refactor(connectors): extract OAuth + ApiKey base services (F020 F021)`.
- [ ] Mark F020, F021, F022, F023, F024, F069 as **RESOLVED**.
