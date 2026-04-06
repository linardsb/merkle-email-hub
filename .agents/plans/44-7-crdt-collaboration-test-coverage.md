# Plan: 44.7 CRDT Collaboration Test Coverage

## Context

The CRDT layer (`app/streaming/crdt/` + `app/streaming/websocket/`) is feature-flagged off (`COLLAB_WS__CRDT_ENABLED`). Existing tests (8 files, ~1,800 lines) cover unit + integration but lack **convergence property tests** (Hypothesis) and a **`collab` marker** for CI gating. Before shipping, we need mathematical guarantees that concurrent edits converge.

## Research Summary

| Area | Files | Current Tests |
|------|-------|---------------|
| CRDT store | `crdt/document_store.py` (8 methods) | 16 tests (286 lines) |
| Sync handler | `crdt/sync_handler.py` (7 methods) | 15 tests (217 lines) |
| Connection manager | `websocket/manager.py` (11 methods) | 19 tests (234 lines) |
| Auth | `websocket/auth.py` (3 functions) | 11 tests (151 lines) |
| Redis bridge | `websocket/redis_bridge.py` (8 methods) | 8 tests (115 lines) |
| WS routes | `websocket/routes.py` | 17 tests (305 lines) |
| CRDT integration | `tests/test_crdt_integration.py` | 12 tests (241 lines) |
| WS integration | `tests/test_websocket_integration.py` | — (254 lines) |

**Key libs:** `pycrdt>=0.12`, `pycrdt-websocket>=0.15`, `hypothesis>=6.100` (available, unused in streaming)

**Config:** `settings.collab_ws.crdt_enabled` (default `False`), `settings.collab_ws.enabled` (default `False`)

**Existing patterns:** `_make_db_row()`, `_make_user()`, `_make_ws()`, `_create_update()` factories. `@pytest.mark.anyio` for async. `AsyncMock` for DB/WS.

## Test Landscape

- **Hypothesis** is in dev deps but not used in streaming tests — opportunity for property-based convergence
- **No `collab` marker** exists in `pyproject.toml`
- **No `make test-collab`** target in Makefile
- Existing `make test` runs `-m "not integration and not benchmark and not visual_regression"` — adding `collab` to exclusion list gates it behind explicit opt-in

## Type Check Baseline

- **Pyright errors: 0** (23 warnings — `reportPrivateUsage` in tests, expected)
- **Mypy errors: 0** (26 source files clean)

## Files to Create/Modify

### New Files
| File | Purpose | ~Lines |
|------|---------|--------|
| `app/streaming/tests/test_crdt_convergence.py` | Deterministic convergence unit tests | ~250 |
| `app/streaming/tests/test_crdt_properties.py` | Hypothesis property-based convergence | ~200 |
| `app/streaming/tests/conftest.py` | Shared fixtures for convergence tests | ~80 |

### Modified Files
| File | Change |
|------|--------|
| `pyproject.toml:257-261` | Add `collab` marker |
| `Makefile:48` | Add `collab` to default exclusion; add `test-collab` target |

## Implementation Steps

### Step 1: Add `collab` marker + Makefile target

**`pyproject.toml:257-261`** — add marker:
```python
markers = [
    "integration: ...",
    "benchmark: ...",
    "visual_regression: ...",
    "collab: CRDT collaboration tests (run with: make test-collab)",
]
```

**`Makefile:48`** — exclude collab from default `make test`:
```makefile
test:
	uv run pytest -v -m "not integration and not benchmark and not visual_regression and not collab"
```

**`Makefile`** — add new target after `test-properties` (line ~60):
```makefile
test-collab: ## Run CRDT collaboration tests
	COLLAB_WS__ENABLED=true COLLAB_WS__CRDT_ENABLED=true uv run pytest -v -m collab
```

### Step 2: Create shared fixtures — `app/streaming/tests/conftest.py`

Fixtures for convergence tests:
```python
import pycrdt, pytest
from typing import Any

@pytest.fixture
def doc_pair() -> tuple[pycrdt.Doc, pycrdt.Doc]:
    """Two independent Yjs documents for convergence testing."""
    return pycrdt.Doc(), pycrdt.Doc()

def sync_docs(*docs: pycrdt.Doc) -> None:
    """Bidirectional sync: exchange state vectors + apply deltas."""
    for i, d1 in enumerate(docs):
        for j, d2 in enumerate(docs):
            if i != j:
                sv = d2.get_state()          # state vector of target
                update = d1.get_update(sv)    # delta from source
                d2.apply_update(update)

def get_text(doc: pycrdt.Doc) -> str:
    return str(doc.get("content", type=pycrdt.Text))

def apply_insert(doc: pycrdt.Doc, pos: int, text: str) -> None:
    t = doc.get("content", type=pycrdt.Text)
    # Clamp position to valid range
    length = len(str(t))
    pos = min(pos, length)
    t[pos:pos] = text  # insert at position via slice

def apply_delete(doc: pycrdt.Doc, pos: int, length: int = 1) -> None:
    t = doc.get("content", type=pycrdt.Text)
    text_len = len(str(t))
    if text_len == 0 or pos >= text_len:
        return
    end = min(pos + length, text_len)
    del t[pos:end]
```

### Step 3: Create convergence unit tests — `app/streaming/tests/test_crdt_convergence.py`

~12 deterministic tests covering:

```
@pytest.mark.collab
class TestTwoClientConvergence:
    test_concurrent_inserts_at_same_position     — both insert at pos 0, both words present
    test_concurrent_inserts_at_different_positions — order preserved
    test_concurrent_insert_and_delete             — no data loss from delete
    test_sequential_edits_converge                — apply in different order, same result
    test_three_clients_converge                   — 3-way sync
    test_empty_documents_converge                 — trivial case

@pytest.mark.collab
class TestOfflineReconnection:
    test_offline_edits_merge_on_reconnect         — apply offline, sync, converge
    test_long_offline_divergence                  — many edits offline, still converge
    test_offline_delete_vs_online_insert          — concurrent delete+insert across disconnect

@pytest.mark.collab
class TestEdgeCases:
    test_duplicate_update_idempotent              — applying same update twice is safe
    test_empty_update_no_op                       — empty update doesn't corrupt state
    test_large_document_convergence               — 1000 chars, still converges
```

Each test follows pattern:
1. Create 2+ `pycrdt.Doc()` instances
2. Apply operations independently (no sync yet)
3. Call `sync_docs()` to exchange updates
4. Assert `get_text(doc1) == get_text(doc2)`

### Step 4: Create property-based tests — `app/streaming/tests/test_crdt_properties.py`

Hypothesis strategies + properties:

```python
@pytest.mark.collab
class TestConvergenceProperties:

    @given(ops1=st.lists(edit_op_strategy(), max_size=20),
           ops2=st.lists(edit_op_strategy(), max_size=20))
    @settings(max_examples=200, deadline=timedelta(seconds=5))
    def test_two_client_convergence_property(ops1, ops2):
        """Any two sequences of concurrent ops converge after sync."""

    @given(ops=st.lists(edit_op_strategy(), max_size=30))
    @settings(max_examples=100)
    def test_self_sync_idempotent(ops):
        """Syncing a doc with itself doesn't change state."""

    @given(ops1=..., ops2=..., ops3=...)
    @settings(max_examples=100)
    def test_three_client_convergence(ops1, ops2, ops3):
        """Three concurrent editors always converge."""

    @given(ops=st.lists(edit_op_strategy(), max_size=20),
           order=st.permutations(range(N)))
    def test_update_order_independence(ops, order):
        """Applying updates in any order yields same state."""
```

**Strategy:**
```python
@st.composite
def edit_op_strategy(draw):
    op_type = draw(st.sampled_from(["insert", "delete"]))
    pos = draw(st.integers(min_value=0, max_value=50))
    if op_type == "insert":
        text = draw(st.text(min_size=1, max_size=5, alphabet=st.characters(whitelist_categories=("L", "N"))))
        return ("insert", pos, text)
    else:
        length = draw(st.integers(min_value=1, max_value=5))
        return ("delete", pos, length)
```

### Step 5: WebSocket integration test (in `test_crdt_convergence.py`)

Add 2-3 tests that exercise the sync handler layer (not raw pycrdt):

```python
@pytest.mark.collab
class TestSyncHandlerConvergence:
    async def test_two_clients_through_sync_handler(self):
        """Two clients sync via YjsSyncHandler, docs converge."""
        store = YjsDocumentStore(...)
        handler = YjsSyncHandler(store)
        # Client A inits room, sends SyncStep1
        # Client B inits room, sends SyncStep1
        # Exchange SyncStep2 messages
        # Both apply updates
        # Verify convergence via store.get_full_state()

    async def test_update_broadcast_convergence(self):
        """Updates sent via handler broadcast to all peers."""
```

## Preflight Warnings

- `pycrdt.Doc.get_state()` returns the **state vector** (for sync), not the full state. Use `doc.get_update()` for full state bytes and `doc.get_update(peer_state_vector)` for delta. Verify API before writing tests.
- `pycrdt.Text` insertion uses slice assignment `t[pos:pos] = text`, not `t.insert()`. Confirm current API.
- Hypothesis `deadline` should be generous (5s) since pycrdt operations involve native code.
- Existing tests use `@pytest.mark.anyio` for async — new async tests must use the same marker.

## Security Checklist

No new endpoints. Tests only — no security surface changes.

## Verification

- [ ] `make test` passes (collab tests excluded by default)
- [ ] `make test-collab` runs all `@pytest.mark.collab` tests
- [ ] 12+ deterministic convergence tests pass
- [ ] Hypothesis runs 200+ examples, all converge
- [ ] 2+ sync handler integration tests pass
- [ ] `make test-collab` completes in <30 seconds
- [ ] Pyright errors ≤ 0 (baseline: 0)
- [ ] Mypy errors ≤ 0 (baseline: 0)
- [ ] Total: 15+ new tests
