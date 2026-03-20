# Plan: Briefs Backend — Connect Project Management Platforms

**Status:** Complete
**Created:** 2026-03-19

## Objective

Implement a full backend for the Briefs module — connecting 8 project management platforms (Jira, Asana, Monday.com, ClickUp, Trello, Notion, Wrike, Basecamp) to import campaign briefs and tasks. The frontend UI already exists and calls specific API endpoints. This plan builds the backend to serve them.

---

## Architecture

Follows the same patterns as `app/connectors/` (ESP sync) and `app/design_sync/` (Figma/Penpot):

- **Provider Protocol** — each platform implements a common interface
- **Encrypted credentials** — Fernet + PBKDF2 (same crypto as design_sync)
- **RBAC + BOLA** — role-based access + project-level authorization
- **Repository pattern** — async SQLAlchemy data access layer
- **Rate-limited routes** — thin HTTP delegation to service layer

### File Structure

```
app/briefs/
├── __init__.py
├── models.py              # BriefConnection, BriefItem, BriefResource, BriefAttachment
├── schemas.py             # Pydantic request/response models
├── routes.py              # API endpoints (matches frontend expectations)
├── service.py             # Business logic, BOLA, provider orchestration
├── repository.py          # Database queries
├── exceptions.py          # Feature-specific errors
├── protocol.py            # BriefProvider Protocol definition
├── providers/
│   ├── __init__.py        # PROVIDER_REGISTRY dict
│   ├── jira.py            # Jira Cloud REST API v3
│   ├── asana.py           # Asana REST API
│   ├── monday.py          # Monday.com GraphQL API
│   ├── clickup.py         # ClickUp REST API v2
│   ├── trello.py          # Trello REST API
│   ├── notion.py          # Notion API v1
│   ├── wrike.py           # Wrike REST API v4
│   └── basecamp.py        # Basecamp REST API v4
└── tests/
    ├── test_service.py
    ├── test_routes.py
    └── test_providers.py
```

Plus one Alembic migration for the new tables.

---

## API Contract

The frontend already calls these endpoints. We must implement them exactly.

### Connections

#### `POST /api/v1/briefs/connections` — Create connection
```
Request:  { name, platform, project_url, credentials: {...}, project_id: int|null }
Response: BriefConnection
Role:     developer
```

**Credential shapes by platform:**

| Platform | Fields |
|----------|--------|
| jira | `{ email, api_token }` |
| asana | `{ personal_access_token }` |
| monday | `{ api_key }` |
| clickup | `{ api_token }` |
| trello | `{ api_key, api_token }` |
| notion | `{ integration_token }` |
| wrike | `{ access_token }` |
| basecamp | `{ access_token }` |

On create: validate credentials by calling the platform API, encrypt, store.

#### `GET /api/v1/briefs/connections` — List connections
```
Response: BriefConnection[]
Role:     viewer
```

#### `POST /api/v1/briefs/connections/delete` — Delete connection
```
Request:  { id: int }
Response: { success: bool }
Role:     admin
```

#### `POST /api/v1/briefs/connections/sync` — Trigger sync
```
Request:  { id: int }
Response: BriefConnection (refreshed)
Role:     developer
```

Fetches latest items from the platform API and upserts into DB.

### Items

#### `GET /api/v1/briefs/connections/{connection_id}/items` — Items for connection
```
Response: BriefItem[]
Role:     viewer
```

#### `GET /api/v1/briefs/items` — All items (unified view)
```
Query:    ?platform=jira&status=open&search=summer
Response: BriefItem[]
Role:     viewer
```

#### `GET /api/v1/briefs/items/{item_id}` — Item detail
```
Response: BriefDetail (BriefItem + description, attachments, priority)
Role:     viewer
```

### Import

#### `POST /api/v1/briefs/import` — Import items into project
```
Request:  { brief_item_ids: int[], project_name: string }
Response: { project_id: int }
Role:     developer
```

Creates or finds a project, copies brief data into it.

---

## Database Models

### `brief_connections`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| name | String(200) | User-provided display name |
| platform | String(20) | jira/asana/monday/clickup/trello/notion/wrike/basecamp |
| project_url | String(500) | Full URL to the external project/board |
| external_project_id | String(200) | Extracted from URL (Jira project key, Asana GID, etc.) |
| encrypted_credentials | Text | Fernet-encrypted JSON blob |
| credential_last4 | String(4) | Last 4 chars of primary credential for display |
| status | String(20) | connected/syncing/error/disconnected |
| error_message | Text | Nullable |
| project_id | Integer FK → projects | Nullable — link to hub project |
| last_synced_at | DateTime | Nullable |
| created_by_id | Integer FK → users | |
| created_at | DateTime | TimestampMixin |
| updated_at | DateTime | TimestampMixin |

### `brief_items`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| connection_id | Integer FK → brief_connections | CASCADE delete |
| external_id | String(200) | Platform-specific ID (Jira issue key, Asana GID, etc.) |
| title | String(500) | |
| description | Text | Full HTML/markdown description |
| status | String(20) | open/in_progress/done/cancelled |
| priority | String(20) | high/medium/low — nullable |
| assignees | JSON | `["Alice", "Bob"]` |
| labels | JSON | `["email", "summer-campaign"]` |
| due_date | DateTime | Nullable |
| thumbnail_url | Text | Nullable — data URI or external URL |
| created_at | DateTime | |
| updated_at | DateTime | |

Unique constraint: `(connection_id, external_id)` — prevents duplicates on re-sync.

### `brief_resources`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| item_id | Integer FK → brief_items | CASCADE delete |
| type | String(20) | excel/translation/design/document/image/other |
| filename | String(500) | |
| url | Text | Link to resource in platform |
| size_bytes | BigInteger | Nullable |

### `brief_attachments`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| item_id | Integer FK → brief_items | CASCADE delete |
| filename | String(500) | |
| url | Text | |
| size_bytes | BigInteger | |

---

## Provider Protocol

```python
@runtime_checkable
class BriefProvider(Protocol):
    """Interface that each platform provider must implement."""

    async def validate_credentials(
        self, credentials: dict[str, str], project_url: str
    ) -> bool:
        """Test that credentials are valid. Return True/False."""
        ...

    async def extract_project_id(self, project_url: str) -> str:
        """Extract the platform-specific project/board ID from a URL."""
        ...

    async def list_items(
        self, credentials: dict[str, str], project_id: str
    ) -> list[RawBriefItem]:
        """Fetch all tasks/issues/cards from the external project."""
        ...

    async def get_item(
        self, credentials: dict[str, str], project_id: str, item_id: str
    ) -> RawBriefItem:
        """Fetch a single task/issue with full detail."""
        ...
```

`RawBriefItem` is a normalized dataclass that each provider maps its API response into:

```python
@dataclass
class RawBriefItem:
    external_id: str
    title: str
    description: str
    status: str           # Platform status → mapped to open/in_progress/done/cancelled
    priority: str | None
    assignees: list[str]
    labels: list[str]
    due_date: datetime | None
    thumbnail_url: str | None
    resources: list[RawResource]
    attachments: list[RawAttachment]
```

---

## Provider Implementation Details

### Jira (Cloud REST API v3)

```
Base URL: https://{domain}.atlassian.net/rest/api/3
Auth:     Basic (email:api_token)
Project:  Extract from URL: atlassian.net/jira/software/projects/{KEY}
Endpoints:
  - Validate: GET /myself
  - List:     GET /search?jql=project={key}&maxResults=100
  - Detail:   GET /issue/{issueIdOrKey}?expand=renderedFields
Status map:
  "To Do" → open, "In Progress" → in_progress, "Done" → done
```

### Asana (REST API)

```
Base URL: https://app.asana.com/api/1.0
Auth:     Bearer {personal_access_token}
Project:  Extract GID from URL: app.asana.com/0/{project_gid}
Endpoints:
  - Validate: GET /users/me
  - List:     GET /projects/{gid}/tasks?opt_fields=name,assignee,due_on,completed,...
  - Detail:   GET /tasks/{gid}?opt_fields=name,notes,html_notes,assignee,...
Status map:
  completed=true → done, completed=false → open
```

### Monday.com (GraphQL API)

```
Base URL: https://api.monday.com/v2
Auth:     Authorization: {api_key}
Board:    Extract board ID from URL
Endpoints:
  - Validate: query { me { id name } }
  - List:     query { boards(ids: [{id}]) { items_page { items { id name ... } } } }
  - Detail:   query { items(ids: [{id}]) { id name column_values { ... } } }
Status map:
  Map from "Status" column value
```

### ClickUp (REST API v2)

```
Base URL: https://api.clickup.com/api/v2
Auth:     Authorization: {api_token}
List:     Extract list/folder/space ID from URL
Endpoints:
  - Validate: GET /user
  - List:     GET /list/{list_id}/task?include_closed=true
  - Detail:   GET /task/{task_id}
Status map:
  "to do" → open, "in progress" → in_progress, "complete"/"closed" → done
```

### Trello (REST API)

```
Base URL: https://api.trello.com/1
Auth:     Query params: key={api_key}&token={api_token}
Board:    Extract board ID or short link from URL
Endpoints:
  - Validate: GET /members/me?key=...&token=...
  - List:     GET /boards/{id}/cards?key=...&token=...
  - Detail:   GET /cards/{id}?attachments=true&key=...&token=...
Status map:
  card.closed=true → done, card on "Done" list → done, else → open
```

### Notion (API v1)

```
Base URL: https://api.notion.com/v1
Auth:     Bearer {integration_token}, Notion-Version: 2022-06-28
Database: Extract database/page ID from URL (remove hyphens)
Endpoints:
  - Validate: GET /users/me
  - List:     POST /databases/{id}/query (filter/sort via body)
  - Detail:   GET /pages/{id} + GET /blocks/{id}/children (for content)
Status map:
  Map from "Status" property
```

### Wrike (REST API v4)

```
Base URL: https://www.wrike.com/api/v4
Auth:     Bearer {access_token}
Folder:   Extract folder/project ID from URL
Endpoints:
  - Validate: GET /contacts?me=true
  - List:     GET /folders/{id}/tasks
  - Detail:   GET /tasks/{id}
Status map:
  "Active" → open, "Completed" → done, "Deferred" → cancelled
```

### Basecamp (REST API v4)

```
Base URL: https://3.basecampapi.com/{account_id}
Auth:     Bearer {access_token}
Project:  Extract account + project ID from URL
Endpoints:
  - Validate: GET /authorization.json
  - List:     GET /buckets/{project_id}/todolists/{todolist_id}/todos.json
  - Detail:   GET /buckets/{project_id}/todos/{todo_id}.json
Status map:
  completed=true → done, else → open
```

---

## Sync Flow

When user clicks "Sync" or creates a new connection:

```
1. Decrypt credentials from DB
2. Call provider.validate_credentials() → if fails, set status="error"
3. Call provider.list_items(credentials, project_id)
4. For each RawBriefItem:
   a. Upsert by (connection_id, external_id) — update existing, insert new
   b. Map platform status → normalized status
   c. Upsert resources and attachments
5. Set connection.last_synced_at = now()
6. Set connection.status = "connected"
7. Return updated connection
```

Items removed from the external platform are NOT deleted from the hub (soft retention).

---

## Implementation Order

### Phase 1: Core Infrastructure (models, protocol, service shell)

| # | Task | Files |
|---|------|-------|
| 1 | Create `app/briefs/__init__.py` | |
| 2 | Create database models | `app/briefs/models.py` |
| 3 | Create Alembic migration | `alembic/versions/xxxx_add_briefs_tables.py` |
| 4 | Create exception classes | `app/briefs/exceptions.py` |
| 5 | Create Pydantic schemas | `app/briefs/schemas.py` |
| 6 | Create provider protocol + RawBriefItem | `app/briefs/protocol.py` |
| 7 | Create repository layer | `app/briefs/repository.py` |
| 8 | Create service layer (orchestration) | `app/briefs/service.py` |
| 9 | Create routes (all endpoints) | `app/briefs/routes.py` |
| 10 | Register router in `app/main.py` | `app/main.py` |

### Phase 2: Provider Implementations (one per platform)

Each provider is independent — can be done in parallel.

| # | Provider | File | API Type | Difficulty |
|---|----------|------|----------|------------|
| 11 | Jira | `app/briefs/providers/jira.py` | REST | Medium |
| 12 | Asana | `app/briefs/providers/asana.py` | REST | Easy |
| 13 | Monday.com | `app/briefs/providers/monday.py` | GraphQL | Medium |
| 14 | ClickUp | `app/briefs/providers/clickup.py` | REST | Easy |
| 15 | Trello | `app/briefs/providers/trello.py` | REST | Easy |
| 16 | Notion | `app/briefs/providers/notion.py` | REST | Medium (block-based content) |
| 17 | Wrike | `app/briefs/providers/wrike.py` | REST | Easy |
| 18 | Basecamp | `app/briefs/providers/basecamp.py` | REST | Easy |
| 19 | Provider registry | `app/briefs/providers/__init__.py` | | |

### Phase 3: Tests

| # | Task | File |
|---|------|------|
| 20 | Service unit tests (mock providers) | `app/briefs/tests/test_service.py` |
| 21 | Route tests (mock service) | `app/briefs/tests/test_routes.py` |
| 22 | Provider tests (mock HTTP) | `app/briefs/tests/test_providers.py` |

### Phase 4: Validation

| # | Task |
|---|------|
| 23 | `make check` — lint, types, tests pass |
| 24 | Manual test: create Jira connection from frontend, sync items |
| 25 | Manual test: browse items, view details, import to project |

---

## Configuration

Add to `app/core/config.py`:

```python
class BriefsConfig(BaseModel):
    enabled: bool = True
    sync_timeout: float = 30.0    # HTTP timeout for platform API calls
    max_items_per_sync: int = 500  # Safety cap on items fetched per sync
```

Environment variables:
```
BRIEFS__ENABLED=true
BRIEFS__SYNC_TIMEOUT=30.0
BRIEFS__MAX_ITEMS_PER_SYNC=500
```

No platform-specific API keys in server config — credentials are per-connection, entered by users via the UI, and stored encrypted in the database.

---

## Security

- **Credential encryption:** Fernet (AES-128-CBC) via `app.design_sync.crypto.encrypt_token` / `decrypt_token` — reuse existing crypto module
- **BOLA:** All endpoints verify user has access to the connection's linked project (if any)
- **Rate limiting:** 10/min for mutations, 30/min for reads
- **No secrets in logs:** Log platform name + connection ID only, never credentials
- **Credential validation:** On create, call platform API to verify before storing
- **RBAC:** viewer=read, developer=create/sync/import, admin=delete

---

## What This Does NOT Include

- **OAuth flows** — all 8 platforms support API tokens/PATs. OAuth is optional and can be added per-platform later.
- **Webhooks** — platforms push updates. For now, sync is user-triggered (pull). Webhook receivers can be added per-platform later.
- **Real-time sync** — no background workers. Sync happens on demand when user clicks "Sync".
- **Attachment download** — resources and attachments store URLs only (links back to the platform). No local file storage.
- **Brief-to-template conversion** — importing briefs creates project context but doesn't auto-generate email templates. That's a separate AI pipeline step.
