# Plan: Phase 6 BOLA Fixes (6.1.1–6.1.9)

## Context

OWASP API Security audit (2026-03-06) found Broken Object Level Authorization across 8 modules. Routes authenticate via `get_current_user` but don't verify the user has access to the specific project/resource. The fix pattern is established: `ProjectService.verify_project_access(project_id, user)` at `app/projects/service.py:44`.

**Decisions captured:**
- Knowledge base (6.1.7): Keep global — role-based access sufficient, no changes needed
- AI chat (6.1.9): Add optional `project_id` to `ChatCompletionRequest`, verify when present
- Approval: Fix all 6 endpoints in one pass
- Projects: Fix both PATCH + DELETE
- WebSocket: DB query on subscribe to validate project_id filters
- Tests: Per-module unit tests (~15 new tests)

## Relationship Map

```
ApprovalRequest.project_id → projects.id          (DIRECT)
ExportRecord.build_id → email_builds.id            (INDIRECT)
EmailBuild.project_id → projects.id                (1 hop)
QAResult.build_id → email_builds.id                (INDIRECT, nullable)
QAResult.template_version_id → template_versions.id (INDIRECT, nullable)
RenderingTest.build_id → email_builds.id           (INDIRECT, nullable)
RenderingTest.template_version_id → template_versions.id (INDIRECT, nullable)
```

## Files to Create/Modify

### Service layer changes (add user param + verify_project_access)
- `app/projects/service.py` — Add user param to `update_project()`, `delete_project()`
- `app/approval/service.py` — Add user param to all 6 methods, verify via approval.project_id
- `app/connectors/service.py` — Add user param to `export()`, fetch build to get project_id
- `app/qa_engine/service.py` — Add user param to `override_result()`, fetch build/template for project_id
- `app/rendering/service.py` — Add user param to `compare_tests()`, verify both tests' project_ids
- `app/ai/schemas.py` — Add optional `project_id` field to `ChatCompletionRequest`
- `app/ai/routes.py` — Pass `current_user` + `project_id` to service, verify access
- `app/streaming/routes.py` — Validate project_id filters against user membership

### Route layer changes (pass current_user to service)
- `app/projects/routes.py` — Pass `current_user` to update/delete
- `app/approval/routes.py` — Pass `current_user` to all service calls
- `app/connectors/routes.py` — Pass `current_user` to export
- `app/qa_engine/routes.py` — Already passes user to `override_result`, no route change needed
- `app/rendering/routes.py` — Pass `current_user` to compare

### Tests
- `app/projects/tests/test_bola.py` — NEW: test update/delete denied for non-members
- `app/approval/tests/test_bola.py` — NEW: test all 6 endpoints denied for non-members
- `app/connectors/tests/test_bola.py` — NEW: test export denied for non-member's build
- `app/qa_engine/tests/test_bola.py` — NEW: test override denied for non-member's result
- `app/rendering/tests/test_bola.py` — NEW: test compare denied for non-member's tests
- `app/ai/tests/test_bola.py` — NEW: test chat denied when project_id provided but no access
- `app/streaming/tests/test_bola.py` — NEW: test subscribe with unauthorized project_id rejected

## Implementation Steps

### Step 1: Projects — update_project + delete_project (6.1.1)

**`app/projects/service.py`** — Add `user` param and call `verify_project_access`:

```python
# Line 110: update_project — add user param
async def update_project(self, project_id: int, data: ProjectUpdate, user: User) -> ProjectResponse:
    logger.info("projects.update_started", project_id=project_id, user_id=user.id)
    await self.verify_project_access(project_id, user)
    project = await self.projects.get(project_id)
    if not project:
        raise ProjectNotFoundError(f"Project {project_id} not found")
    project = await self.projects.update(project, data)
    return ProjectResponse.model_validate(project)

# Line 118: delete_project — add user param
async def delete_project(self, project_id: int, user: User) -> None:
    logger.info("projects.delete_started", project_id=project_id, user_id=user.id)
    await self.verify_project_access(project_id, user)
    project = await self.projects.get(project_id)
    if not project:
        raise ProjectNotFoundError(f"Project {project_id} not found")
    await self.projects.delete(project)
```

**`app/projects/routes.py`** — Rename `_current_user` → `current_user`, pass to service:

```python
# Line 117-128: update_project route
async def update_project(
    request: Request,
    project_id: int,
    data: ProjectUpdate,
    service: ProjectService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ProjectResponse:
    _ = request
    return await service.update_project(project_id, data, current_user)

# Line 131-141: delete_project route
async def delete_project(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),
    current_user: User = Depends(require_role("admin")),
) -> None:
    _ = request
    await service.delete_project(project_id, current_user)
```

### Step 2: Approval — all 6 endpoints (6.1.2 + 6.1.5)

**`app/approval/service.py`** — Add `user` param + verify via `approval.project_id`:

Add import at top:
```python
from app.auth.models import User
from app.projects.service import ProjectService
```

Add helper method to class:
```python
async def _verify_approval_access(self, approval_id: int, user: User) -> "ApprovalRequest":
    """Fetch approval and verify user has access to its project."""
    approval = await self.repository.get(approval_id)
    if not approval:
        raise ApprovalNotFoundError(f"Approval {approval_id} not found")
    project_service = ProjectService(self.db)
    await project_service.verify_project_access(approval.project_id, user)
    return approval
```

Update each method:

```python
async def create_approval(self, data: ApprovalCreate, user: User) -> ApprovalResponse:
    logger.info("approval.create_started", build_id=data.build_id)
    project_service = ProjectService(self.db)
    await project_service.verify_project_access(data.project_id, user)
    approval = await self.repository.create(data.build_id, data.project_id, user.id)
    await self.repository.add_audit(approval.id, "submitted", user.id)
    return ApprovalResponse.model_validate(approval)

async def get_approval(self, approval_id: int, user: User) -> ApprovalResponse:
    approval = await self._verify_approval_access(approval_id, user)
    return ApprovalResponse.model_validate(approval)

async def decide(self, approval_id: int, decision: ApprovalDecision, user: User) -> ApprovalResponse:
    approval = await self._verify_approval_access(approval_id, user)
    approval = await self.repository.update_status(
        approval, decision.status, user.id, decision.review_note
    )
    await self.repository.add_audit(approval_id, decision.status, user.id, decision.review_note)
    logger.info("approval.decided", approval_id=approval_id, status=decision.status)
    return ApprovalResponse.model_validate(approval)

async def add_feedback(self, approval_id: int, data: FeedbackCreate, user: User) -> FeedbackResponse:
    await self._verify_approval_access(approval_id, user)
    fb = await self.repository.add_feedback(approval_id, user.id, data.content, data.feedback_type)
    await self.repository.add_audit(approval_id, "feedback_added", user.id)
    return FeedbackResponse.model_validate(fb)

async def list_by_project(self, project_id: int, user: User) -> list[ApprovalResponse]:
    project_service = ProjectService(self.db)
    await project_service.verify_project_access(project_id, user)
    approvals = await self.repository.list_by_project(project_id)
    return [ApprovalResponse.model_validate(a) for a in approvals]

async def get_feedback(self, approval_id: int, user: User) -> list[FeedbackResponse]:
    await self._verify_approval_access(approval_id, user)
    return [
        FeedbackResponse.model_validate(f)
        for f in await self.repository.get_feedback(approval_id)
    ]

async def get_audit_trail(self, approval_id: int, user: User) -> list[AuditResponse]:
    await self._verify_approval_access(approval_id, user)
    return [
        AuditResponse.model_validate(a)
        for a in await self.repository.get_audit_trail(approval_id)
    ]
```

**`app/approval/routes.py`** — Update all handlers to pass `current_user`:

```python
# list_approvals: rename _current_user → current_user, pass to service
return await service.list_by_project(project_id, current_user)

# create_approval: pass user object instead of user_id
return await service.create_approval(data, user=current_user)

# get_approval: rename _current_user → current_user, pass to service
return await service.get_approval(approval_id, current_user)

# decide_approval: pass user object instead of reviewer_id
return await service.decide(approval_id, decision, user=current_user)

# add_feedback: pass user object instead of user_id
return await service.add_feedback(approval_id, data, user=current_user)

# list_feedback: rename _current_user → current_user, pass to service
return await service.get_feedback(approval_id, current_user)

# get_audit_trail: rename _current_user → current_user, pass to service
return await service.get_audit_trail(approval_id, current_user)
```

### Step 3: Connectors — export (6.1.3)

**`app/connectors/service.py`** — Add user param, fetch build to get project_id:

Add imports:
```python
from app.auth.models import User
from app.email_engine.models import EmailBuild
from app.projects.service import ProjectService
from sqlalchemy import select
```

Update `export()`:
```python
async def export(self, data: ExportRequest, user: User) -> ExportResponse:
    """Export an email build to the specified ESP."""
    # Verify user has access to the build's project
    result = await self.db.execute(
        select(EmailBuild).where(EmailBuild.id == data.build_id)
    )
    build = result.scalar_one_or_none()
    if not build:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Build {data.build_id} not found")

    project_service = ProjectService(self.db)
    await project_service.verify_project_access(build.project_id, user)

    provider = self._get_provider(data.connector_type)
    # ... rest unchanged, but replace user_id with user.id ...
    record = ExportRecord(
        build_id=data.build_id,
        connector_type=data.connector_type,
        exported_by_id=user.id,
        status="exporting",
    )
    # ... rest of method unchanged ...
```

**`app/connectors/routes.py`** — Pass user object:
```python
return await service.export(data, user=current_user)
```

### Step 4: QA Engine — override (6.1.4)

**`app/qa_engine/service.py`** — Add project access check to `override_result()`:

Add imports:
```python
from app.email_engine.models import EmailBuild
from app.projects.service import ProjectService
from sqlalchemy import select
```

Add helper to resolve project_id from QA result:
```python
async def _resolve_project_id(self, result: QAResult) -> int | None:
    """Resolve the project_id from a QA result via build or template chain."""
    if result.build_id:
        from app.email_engine.models import EmailBuild
        db_result = await self.db.execute(
            select(EmailBuild.project_id).where(EmailBuild.id == result.build_id)
        )
        project_id = db_result.scalar_one_or_none()
        if project_id:
            return project_id
    # If no build_id or build not found, try template_version chain
    if result.template_version_id:
        from app.templates.models import Template, TemplateVersion
        db_result = await self.db.execute(
            select(Template.project_id)
            .join(TemplateVersion, TemplateVersion.template_id == Template.id)
            .where(TemplateVersion.id == result.template_version_id)
        )
        project_id = db_result.scalar_one_or_none()
        if project_id:
            return project_id
    return None
```

Update `override_result()` — insert access check after fetching result (before line 152):
```python
async def override_result(self, result_id: int, data: QAOverrideRequest, user: User) -> QAOverrideResponse:
    result = await self.repository.get_result_with_checks(result_id)
    if not result:
        raise QAResultNotFoundError(f"QA result {result_id} not found")

    # BOLA check: verify user has access to the result's project
    project_id = await self._resolve_project_id(result)
    if project_id:
        project_service = ProjectService(self.db)
        await project_service.verify_project_access(project_id, user)

    if result.passed:
        raise QAOverrideNotAllowedError("Cannot override a passing QA result")
    # ... rest unchanged ...
```

No route change needed — `override_qa_result` already passes `current_user`.

### Step 5: Rendering — compare (6.1.6)

**`app/rendering/service.py`** — Add user param to `compare_tests()`:

Add imports:
```python
from app.auth.models import User
from app.email_engine.models import EmailBuild
from app.projects.service import ProjectService
from sqlalchemy import select
```

Add helper:
```python
async def _resolve_test_project_id(self, test: RenderingTest) -> int | None:
    """Resolve project_id from a rendering test via build link."""
    if test.build_id:
        result = await self.db.execute(
            select(EmailBuild.project_id).where(EmailBuild.id == test.build_id)
        )
        return result.scalar_one_or_none()
    return None
```

Update `compare_tests()`:
```python
async def compare_tests(self, data: RenderingComparisonRequest, user: User) -> RenderingComparisonResponse:
    baseline = await self.repository.get_test(data.baseline_test_id)
    current = await self.repository.get_test(data.current_test_id)

    if not baseline:
        raise RenderingTestNotFoundError(f"Baseline test {data.baseline_test_id} not found")
    if not current:
        raise RenderingTestNotFoundError(f"Current test {data.current_test_id} not found")

    # BOLA check: verify user has access to both tests' projects
    project_service = ProjectService(self.db)
    for test in [baseline, current]:
        project_id = await self._resolve_test_project_id(test)
        if project_id:
            await project_service.verify_project_access(project_id, user)

    # ... rest unchanged ...
```

**`app/rendering/routes.py`** — Rename `_current_user` → `current_user`, pass to service:
```python
# Line 75-85: compare endpoint
async def compare_rendering_tests(
    request: Request,
    data: RenderingComparisonRequest,
    service: RenderingService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> RenderingComparisonResponse:
    _ = request
    return await service.compare_tests(data, current_user)
```

### Step 6: AI Chat — optional project_id (6.1.9)

**`app/ai/schemas.py`** — Add `project_id` field to `ChatCompletionRequest`:

```python
class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    model: str | None = None
    stream: bool = False
    task_tier: Literal["complex", "standard", "lightweight"] | None = None
    project_id: int | None = None  # Optional project context for BOLA verification
```

**`app/ai/routes.py`** — Verify project access when project_id provided:

```python
# Line 112-158: chat_completions route
@router.post("/chat/completions", response_model=None)
@limiter.limit("20/minute")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db),
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_user),  # renamed from _current_user
) -> ChatCompletionResponse | StreamingResponse:
    # Check daily quota
    client_ip = _get_client_ip(request)
    tracker = _get_quota_tracker()
    if not await tracker.check_and_increment(client_ip):
        remaining = await tracker.get_remaining(client_ip)
        logger.warning("ai.quota_exceeded_http", client_ip=client_ip, remaining=remaining)
        raise HTTPException(
            status_code=429,
            detail=f"Daily query quota exceeded. Remaining: {remaining}. Resets in 24 hours.",
        )

    # BOLA check: verify project access when project_id is provided
    if body.project_id is not None:
        from app.projects.service import ProjectService
        project_service = ProjectService(db)
        await project_service.verify_project_access(body.project_id, current_user)

    if body.stream:
        return StreamingResponse(
            service.stream_chat(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    return await service.chat(body)
```

Add `get_db` import at top:
```python
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
```

### Step 7: WebSocket — validate project_id filters (6.1.8)

**`app/streaming/routes.py`** — Add project access validation on subscribe:

Add imports at top:
```python
from app.auth.repository import AuthRepository
from app.core.database import AsyncSessionLocal
```

After line 110 (`user_id = payload.sub`), resolve the User object:
```python
user_id = payload.sub

# Resolve User object for authorization checks
async with AsyncSessionLocal() as auth_db:
    auth_repo = AuthRepository(auth_db)
    ws_user = await auth_repo.find_by_id(int(user_id))
if not ws_user:
    await websocket.close(code=4001, reason="Authentication failed")
    logger.warning("streaming.ws.auth_failed", reason="user_not_found", user_id=user_id)
    return
```

In the subscribe handler (after line 148), add project_id validation:
```python
if action == "subscribe":
    try:
        msg = WsSubscribeMessage.model_validate(data)
        new_filters: dict[str, str | None] = {}
        if msg.filters:
            for key, value in msg.filters.items():
                new_filters[key] = value

        # BOLA check: validate project_id filter
        filter_project_id = new_filters.get("project_id")
        if filter_project_id is not None:
            from app.projects.service import ProjectService
            try:
                async with AsyncSessionLocal() as project_db:
                    project_service = ProjectService(project_db)
                    await project_service.verify_project_access(
                        int(filter_project_id), ws_user
                    )
            except Exception:
                error_msg = WsError(
                    code="access_denied",
                    message="Access denied to project",
                )
                await websocket.send_json(error_msg.model_dump())
                logger.warning(
                    "streaming.ws.project_access_denied",
                    user_id=user_id,
                    project_id=filter_project_id,
                )
                continue

        manager.update_filters(websocket, new_filters)
        # ... rest unchanged ...
```

### Step 8: Tests

Each test file follows the same pattern: mock the DB session, mock the repository, create a mock user who is NOT a member, and verify `ProjectAccessDeniedError` (403) is raised.

**`app/projects/tests/test_bola.py`**:
```python
"""BOLA authorization tests for project endpoints."""
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.projects.exceptions import ProjectAccessDeniedError
from app.projects.schemas import ProjectUpdate
from app.projects.service import ProjectService


@pytest.fixture
def service() -> ProjectService:
    mock_db = AsyncMock()
    svc = ProjectService(mock_db)
    svc.projects = AsyncMock()
    svc.orgs = AsyncMock()
    return svc


def make_non_member_user(user_id: int = 99) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = "developer"  # not admin
    return user


async def test_update_project_denied_for_non_member(service):
    """Non-member developer cannot update a project."""
    project = MagicMock()
    project.id = 1
    project.deleted_at = None
    service.projects.get = AsyncMock(return_value=project)
    service.projects.get_member = AsyncMock(return_value=None)  # not a member

    user = make_non_member_user()
    with pytest.raises(ProjectAccessDeniedError):
        await service.update_project(1, ProjectUpdate(name="hack"), user)


async def test_delete_project_denied_for_non_member(service):
    """Non-member admin-role user still needs project access for delete."""
    project = MagicMock()
    project.id = 1
    project.deleted_at = None
    service.projects.get = AsyncMock(return_value=project)
    service.projects.get_member = AsyncMock(return_value=None)

    user = make_non_member_user()
    with pytest.raises(ProjectAccessDeniedError):
        await service.delete_project(1, user)


async def test_update_project_allowed_for_admin(service):
    """Admin users bypass project membership check."""
    project = MagicMock()
    project.id = 1
    project.deleted_at = None
    service.projects.get = AsyncMock(return_value=project)
    service.projects.update = AsyncMock(return_value=project)

    user = MagicMock()
    user.id = 1
    user.role = "admin"
    result = await service.update_project(1, ProjectUpdate(name="ok"), user)
    assert result is not None
```

**`app/approval/tests/test_bola.py`**:
```python
"""BOLA authorization tests for approval endpoints."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.approval.service import ApprovalService
from app.projects.exceptions import ProjectAccessDeniedError


@pytest.fixture
def service() -> ApprovalService:
    mock_db = AsyncMock()
    svc = ApprovalService(mock_db)
    svc.repository = AsyncMock()
    return svc


def make_non_member() -> MagicMock:
    user = MagicMock()
    user.id = 99
    user.role = "developer"
    return user


def make_approval(project_id: int = 1) -> MagicMock:
    approval = MagicMock()
    approval.id = 10
    approval.project_id = project_id
    return approval


async def test_get_approval_denied_for_non_member(service):
    service.repository.get = AsyncMock(return_value=make_approval())
    with patch.object(
        ProjectService, "verify_project_access", side_effect=ProjectAccessDeniedError("denied")
    ):
        with pytest.raises(ProjectAccessDeniedError):
            await service.get_approval(10, make_non_member())


async def test_decide_denied_for_non_member(service):
    service.repository.get = AsyncMock(return_value=make_approval())
    with patch.object(
        ProjectService, "verify_project_access", side_effect=ProjectAccessDeniedError("denied")
    ):
        with pytest.raises(ProjectAccessDeniedError):
            from app.approval.schemas import ApprovalDecision
            decision = ApprovalDecision(status="approved")
            await service.decide(10, decision, make_non_member())


async def test_list_by_project_denied_for_non_member(service):
    with patch.object(
        ProjectService, "verify_project_access", side_effect=ProjectAccessDeniedError("denied")
    ):
        with pytest.raises(ProjectAccessDeniedError):
            await service.list_by_project(1, make_non_member())
```

Pattern for remaining test files (connectors, qa_engine, rendering, ai, streaming):
- Mock the DB session and repository
- Mock `ProjectService.verify_project_access` to raise `ProjectAccessDeniedError`
- Assert the service method raises 403
- Add one positive test confirming access works when `verify_project_access` succeeds

### Step 9: Knowledge base (6.1.7) — NO CHANGES

Knowledge base is global. Route-level role checks (`require_role("admin", "developer")`) are already enforced. Mark 6.1.7 as done.

## Implementation Order

1. **Step 1** — Projects (foundation, all other modules import from here)
2. **Step 2** — Approval (most endpoints, highest impact)
3. **Step 3** — Connectors
4. **Step 4** — QA Engine
5. **Step 5** — Rendering
6. **Step 6** — AI Chat
7. **Step 7** — WebSocket
8. **Step 8** — Tests (can be written alongside each step)
9. **Step 9** — Mark 6.1.7 done in TODO.md

## Verification

- [ ] `make lint` passes
- [ ] `make types` passes
- [ ] `make test` passes (including ~15 new BOLA tests)
- [ ] Each affected endpoint returns 403 for non-member users
- [ ] Admin users bypass project membership checks (existing behavior preserved)
- [ ] Existing tests unchanged and passing
- [ ] No circular imports introduced
