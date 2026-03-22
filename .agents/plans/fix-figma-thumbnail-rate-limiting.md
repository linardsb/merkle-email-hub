# Plan: Fix Figma Thumbnail Rate Limiting

## Context

Thumbnails in the design file browser (`DesignFileBrowser`) are not loading. The root cause is **Figma API rate limiting (HTTP 429)** combined with several architectural gaps:

1. **No retry/backoff** — `export_images` fires all batches concurrently via `asyncio.gather` with zero delay, hitting Figma's rate limit (~30 req/min per PAT)
2. **429 = silent failure** — The frontend catches the error silently (`catch {}`) and shows empty thumbnails with no user feedback
3. **No caching** — Every component mount re-fetches all thumbnails from Figma, multiplying API calls
4. **Greedy collection** — `collectFrameIds()` walks the entire tree and sends up to 100 node IDs in one go, even for deeply nested files like the EmailLove template (10+ mj-wrapper frames)

The file structure itself loads fine (as shown in the screenshot) because `get_file_structure` is a single API call, but the subsequent `export_images` call triggers a second request immediately, and for files with many nodes, multiple concurrent batches.

## Files to Modify

1. `app/design_sync/figma/service.py` — Add sequential batch delay + retry with exponential backoff for 429s
2. `app/design_sync/service.py` — Add Redis-based thumbnail URL caching (URLs valid for ~14 days)
3. `cms/apps/web/src/components/design-sync/design-file-browser.tsx` — Limit thumbnail requests to visible/expanded nodes, show loading state, surface rate limit errors
4. `app/design_sync/tests/test_service.py` — Add tests for retry logic and caching

## Implementation Steps

### Step 1: Add retry with backoff to `FigmaDesignSyncService.export_images`

In `app/design_sync/figma/service.py`, modify the `_fetch_batch` inner function:

```python
async def _fetch_batch(batch: list[str]) -> dict[str, Any]:
    max_retries = 3
    for attempt in range(max_retries):
        resp = await client.get(
            f"{_FIGMA_API}/v1/images/{file_ref}",
            headers=headers,
            params={
                "ids": ",".join(batch),
                "format": format,
                "scale": str(scale),
            },
        )
        if resp.status_code == 429:
            if attempt < max_retries - 1:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                wait = min(retry_after, 30)  # cap at 30s
                logger.warning(
                    "design_sync.figma.rate_limited",
                    attempt=attempt + 1,
                    retry_after=wait,
                )
                await asyncio.sleep(wait)
                continue
            raise SyncFailedError(
                f"Figma API rate limit exceeded after {max_retries} retries. "
                f"Try again in {resp.headers.get('Retry-After', '60')} seconds."
            )
        if resp.status_code == 403:
            raise SyncFailedError("Figma access denied.")
        if resp.status_code != 200:
            raise SyncFailedError(f"Figma images API error (HTTP {resp.status_code})")
        result: dict[str, Any] = resp.json()
        return result
    # Unreachable, but satisfies type checker
    raise SyncFailedError("Figma export failed")
```

**Also change batch execution from concurrent to sequential with a small delay:**

Replace:
```python
results = await asyncio.gather(*[_fetch_batch(b) for b in batches])
```

With:
```python
results: list[dict[str, Any]] = []
for batch in batches:
    result = await _fetch_batch(batch)
    results.append(result)
    if len(batches) > 1:
        await asyncio.sleep(1.0)  # Rate limit courtesy delay
```

### Step 2: Add thumbnail URL caching in `DesignSyncService.export_images`

In `app/design_sync/service.py`, add Redis caching around the export call. Thumbnail URLs from Figma are valid for ~14 days, so cache for 12 days:

```python
async def export_images(self, ...) -> ImageExportResponse:
    """Export images for nodes in a connection."""
    conn = await self._repo.get_connection(connection_id)
    if conn is None:
        raise ConnectionNotFoundError(f"Connection {connection_id} not found")
    if conn.project_id is not None:
        await self._verify_access(conn.project_id, user)

    # Check Redis cache first
    from app.core.config import get_settings
    import redis.asyncio as aioredis
    import json

    settings = get_settings()
    cache_key = f"design_thumbnails:{connection_id}:{format}:{scale}"
    cached_images: dict[str, dict[str, str]] = {}
    uncached_ids: list[str] = list(node_ids)

    try:
        redis = aioredis.from_url(settings.redis.url)
        raw = await redis.get(cache_key)
        if raw:
            cached_images = json.loads(raw)
            uncached_ids = [nid for nid in node_ids if nid not in cached_images]
        await redis.aclose()
    except Exception:
        pass  # Cache miss is fine

    # Only call Figma for uncached nodes
    all_image_responses: list[ExportedImageResponse] = []

    # Serve from cache
    for nid in node_ids:
        if nid in cached_images:
            ci = cached_images[nid]
            all_image_responses.append(
                ExportedImageResponse(
                    node_id=nid,
                    url=ci["url"],
                    format=ci["format"],
                    expires_at=datetime.fromisoformat(ci["expires_at"]) if ci.get("expires_at") else None,
                )
            )

    if uncached_ids:
        provider = self._get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        images = await provider.export_images(
            conn.file_ref, access_token, uncached_ids, format=format, scale=scale
        )
        for img in images:
            resp_img = ExportedImageResponse(
                node_id=img.node_id, url=img.url, format=img.format, expires_at=img.expires_at
            )
            all_image_responses.append(resp_img)
            cached_images[img.node_id] = {
                "url": img.url,
                "format": img.format,
                "expires_at": img.expires_at.isoformat() if img.expires_at else "",
            }

        # Update cache (12 day TTL — Figma URLs expire in ~14 days)
        try:
            redis = aioredis.from_url(settings.redis.url)
            await redis.set(cache_key, json.dumps(cached_images), ex=12 * 86400)
            await redis.aclose()
        except Exception:
            pass

    return ImageExportResponse(
        connection_id=connection_id,
        images=all_image_responses,
        total=len(all_image_responses),
    )
```

### Step 3: Frontend — Lazy thumbnail loading + error feedback

In `cms/apps/web/src/components/design-sync/design-file-browser.tsx`:

**3a. Only fetch thumbnails for top-level frames (not deeply nested nodes):**

Replace `collectFrameIds` to only collect direct page children (depth=1):

```typescript
/** Collect IDs of direct child frames (depth=1) for initial thumbnails */
function collectTopLevelFrameIds(pages: DesignNode[]): string[] {
  const ids: string[] = [];
  for (const page of pages) {
    for (const child of page.children) {
      if (THUMBNAIL_TYPES.has(child.type)) {
        ids.push(child.id);
      }
    }
  }
  return ids;
}
```

**3b. Show a loading indicator while thumbnails load:**

Add a `thumbnailsLoading` state:
```typescript
const [thumbnailsLoading, setThumbnailsLoading] = useState(false);
```

In the effect, set it before/after the fetch.

**3c. Surface rate limit errors:**

Instead of silently catching, show a subtle warning:
```typescript
const [thumbnailError, setThumbnailError] = useState<string | null>(null);

// In the catch:
catch (err) {
  setThumbnailError("Thumbnails unavailable — Figma rate limit. They'll load on next visit.");
}
```

Render below the header:
```tsx
{thumbnailError && (
  <p className="mb-1 text-xs text-foreground-muted">{thumbnailError}</p>
)}
```

### Step 4: Tests

In `app/design_sync/tests/test_service.py`:

1. **Test retry on 429** — Mock `httpx.AsyncClient` to return 429 on first call, 200 on second. Verify `export_images` succeeds after retry.
2. **Test max retries exceeded** — Return 429 on all 3 attempts, verify `SyncFailedError` is raised.
3. **Test caching** — Call `export_images` twice, verify Figma API is only called once (second call serves from Redis mock).

## Security Checklist (scoped to this feature's endpoints)

No new endpoints. Changes are to existing `export_images` internals:
- [x] Auth dependency — no change (existing `require_role("developer")`)
- [x] Rate limiting — no change (existing `@limiter.limit`)
- [x] Input validation — no change (existing Pydantic schemas)
- [x] Error responses — retry logic still uses `SyncFailedError` (auto-sanitized)
- [x] No secrets in logs — only logging attempt count and wait time
- [x] Redis cache key uses connection_id (scoped per-user connection, BOLA check happens before cache)

## Verification

- [ ] `make check` passes
- [ ] With a real Figma file: thumbnails load on first visit, load instantly on second visit (cached)
- [ ] With 429 response: retry succeeds after backoff, frontend shows warning if all retries fail
- [ ] Deeply nested files (like EmailLove) no longer fire 100 thumbnail requests
