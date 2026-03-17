"""Tests for the versioned prompt template store (Phase 22.2)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.ai.agents.skill_override import (
    _overrides,
    _store_cache,
    clear_store_cache,
    get_override,
    set_override,
    set_store_cache,
)
from app.ai.prompt_store import (
    PromptStoreService,
    PromptTemplate,
    PromptTemplateRepository,
    preload_prompt_store_cache,
)
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.main import app

# ── Helpers ──


def _make_user(role: str = "developer") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_template(
    *,
    id: int = 1,
    agent_id: str = "scaffolder",
    variant: str = "default",
    version: int = 1,
    content: str = "test prompt",
    active: bool = True,
    description: str | None = None,
    created_by: str | None = None,
) -> PromptTemplate:
    t = PromptTemplate(
        id=id,
        agent_id=agent_id,
        variant=variant,
        version=version,
        content=content,
        active=active,
        description=description,
        created_by=created_by,
    )
    t.created_at = datetime.now(UTC)
    return t


# ── Repository tests ──


class TestPromptTemplateRepository:
    """Unit tests for PromptTemplateRepository with mocked DB."""

    @pytest.mark.asyncio
    async def test_get_active_returns_template(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = _make_template()
        db.execute.return_value = result_mock

        repo = PromptTemplateRepository(db)
        result = await repo.get_active("scaffolder")
        assert result is not None
        assert result.agent_id == "scaffolder"
        assert result.active is True

    @pytest.mark.asyncio
    async def test_get_active_returns_none_when_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        repo = PromptTemplateRepository(db)
        result = await repo.get_active("scaffolder")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_template(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = _make_template(id=5)
        db.execute.return_value = result_mock

        repo = PromptTemplateRepository(db)
        result = await repo.get_by_id(5)
        assert result is not None
        assert result.id == 5

    @pytest.mark.asyncio
    async def test_list_versions_returns_ordered(self) -> None:
        db = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [
            _make_template(version=3),
            _make_template(version=2),
            _make_template(version=1),
        ]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        repo = PromptTemplateRepository(db)
        versions = await repo.list_versions("scaffolder")
        assert len(versions) == 3
        assert versions[0].version == 3

    @pytest.mark.asyncio
    async def test_list_agents_distinct(self) -> None:
        db = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = ["dark_mode", "scaffolder"]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        repo = PromptTemplateRepository(db)
        agents = await repo.list_agents()
        assert agents == ["dark_mode", "scaffolder"]

    @pytest.mark.asyncio
    async def test_create_first_version(self) -> None:
        """First version for a new agent+variant should be version 1."""
        db = AsyncMock()
        # First call: max version query returns 0
        version_result = MagicMock()
        version_result.scalar_one.return_value = 0
        db.execute.return_value = version_result
        db.flush = AsyncMock()

        repo = PromptTemplateRepository(db)
        template = await repo.create(
            agent_id="scaffolder",
            variant="default",
            content="new prompt",
        )
        assert template.version == 1
        assert template.active is False
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_increments_version(self) -> None:
        """Next version should be max+1."""
        db = AsyncMock()
        version_result = MagicMock()
        version_result.scalar_one.return_value = 3
        db.execute.return_value = version_result
        db.flush = AsyncMock()

        repo = PromptTemplateRepository(db)
        template = await repo.create(
            agent_id="scaffolder",
            variant="default",
            content="updated prompt",
        )
        assert template.version == 4

    @pytest.mark.asyncio
    async def test_activate_deactivates_others(self) -> None:
        """Activation should deactivate all then activate the target."""
        db = AsyncMock()
        target = _make_template(id=2, active=False)

        # get_by_id returns target
        get_result = MagicMock()
        get_result.scalar_one_or_none.return_value = target
        db.execute.return_value = get_result
        db.flush = AsyncMock()

        repo = PromptTemplateRepository(db)
        result = await repo.activate(2)
        assert result is not None
        assert result.active is True
        # execute called: 1 for get_by_id + 1 for bulk deactivation
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_activate_returns_none_for_missing(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        repo = PromptTemplateRepository(db)
        result = await repo.activate(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_rollback_returns_none_on_v1(self) -> None:
        """Can't rollback past version 1."""
        db = AsyncMock()
        active = _make_template(version=1, active=True)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = active
        db.execute.return_value = result_mock

        repo = PromptTemplateRepository(db)
        result = await repo.rollback("scaffolder")
        assert result is None

    @pytest.mark.asyncio
    async def test_rollback_returns_none_when_no_active(self) -> None:
        """No active prompt → can't rollback."""
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        repo = PromptTemplateRepository(db)
        result = await repo.rollback("scaffolder")
        assert result is None


# ── Service tests ──


class TestPromptStoreService:
    @pytest.mark.asyncio
    async def test_get_prompt_returns_content(self) -> None:
        db = AsyncMock()
        template = _make_template(content="Hello world")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = template
        db.execute.return_value = result_mock

        service = PromptStoreService()
        content = await service.get_prompt(db, "scaffolder")
        assert content == "Hello world"

    @pytest.mark.asyncio
    async def test_get_prompt_returns_none_when_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        service = PromptStoreService()
        content = await service.get_prompt(db, "scaffolder")
        assert content is None

    @pytest.mark.asyncio
    async def test_seed_from_skill_files(self) -> None:
        """Seeding should create entries for agents with SKILL.md files."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()

        # list_agents returns empty
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        list_result = MagicMock()
        list_result.scalars.return_value = scalars_mock

        # create version query returns 0
        version_result = MagicMock()
        version_result.scalar_one.return_value = 0

        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return list_result
            if call_count % 3 == 2:  # create version query
                return version_result
            # activate get_by_id + bulk deactivate
            tpl = _make_template(active=False, version=1)
            r = MagicMock()
            r.scalar_one_or_none.return_value = tpl
            return r

        db.execute = AsyncMock(side_effect=side_effect)

        service = PromptStoreService()

        def _make_skill_path(agent: str) -> MagicMock:
            path = MagicMock()
            skill = MagicMock()
            skill.exists.return_value = agent in ("scaffolder", "dark_mode")
            skill.read_text.return_value = f"SKILL content for {agent}"
            path.__truediv__ = MagicMock(return_value=skill)
            return path

        with patch("app.ai.agents.skills_routes.AGENTS_DIR") as mock_dir:
            mock_dir.__truediv__ = MagicMock(side_effect=_make_skill_path)

            with patch(
                "app.ai.agents.skills_routes.AGENT_NAMES",
                ["scaffolder", "dark_mode", "content"],
            ):
                seeded = await service.seed_from_skill_files(db)

        assert "scaffolder" in seeded
        assert "dark_mode" in seeded
        assert "content" not in seeded  # no SKILL.md

    @pytest.mark.asyncio
    async def test_seed_skips_existing(self) -> None:
        """Seeding should skip agents that already have DB entries."""
        db = AsyncMock()
        db.commit = AsyncMock()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = ["scaffolder"]
        list_result = MagicMock()
        list_result.scalars.return_value = scalars_mock
        db.execute.return_value = list_result

        service = PromptStoreService()
        with patch("app.ai.agents.skills_routes.AGENT_NAMES", ["scaffolder"]):
            seeded = await service.seed_from_skill_files(db)

        assert seeded == {}


# ── Skill override integration tests ──


class TestSkillOverrideIntegration:
    def setup_method(self) -> None:
        _overrides.clear()
        _store_cache.clear()

    def teardown_method(self) -> None:
        _overrides.clear()
        _store_cache.clear()

    @patch("app.ai.agents.skill_override.get_settings")
    def test_get_override_prefers_store_cache(self, mock_settings: MagicMock) -> None:
        """Store cache beats in-memory override."""
        mock_settings.return_value.ai.prompt_store_enabled = True
        set_override("scaffolder", "memory content")
        set_store_cache("scaffolder", "store content")
        assert get_override("scaffolder") == "store content"

    @patch("app.ai.agents.skill_override.get_settings")
    def test_get_override_falls_back_to_memory(self, mock_settings: MagicMock) -> None:
        """When store disabled, falls back to in-memory override."""
        mock_settings.return_value.ai.prompt_store_enabled = False
        set_override("scaffolder", "memory content")
        set_store_cache("scaffolder", "store content")
        assert get_override("scaffolder") == "memory content"

    @patch("app.ai.agents.skill_override.get_settings")
    def test_get_override_returns_none(self, mock_settings: MagicMock) -> None:
        """Both empty → None."""
        mock_settings.return_value.ai.prompt_store_enabled = True
        assert get_override("scaffolder") is None

    def test_clear_store_cache_all(self) -> None:
        set_store_cache("scaffolder", "a")
        set_store_cache("dark_mode", "b")
        clear_store_cache()
        assert len(_store_cache) == 0

    def test_clear_store_cache_specific(self) -> None:
        set_store_cache("scaffolder", "a")
        set_store_cache("dark_mode", "b")
        clear_store_cache("scaffolder")
        assert "scaffolder" not in _store_cache
        assert "dark_mode" in _store_cache

    @pytest.mark.asyncio
    async def test_preload_populates_cache(self) -> None:
        """preload_prompt_store_cache fills cache from DB."""
        db = AsyncMock()

        # list_agents returns 1 agent
        agents_scalars = MagicMock()
        agents_scalars.all.return_value = ["scaffolder"]
        agents_result = MagicMock()
        agents_result.scalars.return_value = agents_scalars

        # get_active returns a template
        template = _make_template(content="cached content")
        active_result = MagicMock()
        active_result.scalar_one_or_none.return_value = template

        db.execute = AsyncMock(side_effect=[agents_result, active_result])

        with patch("app.ai.prompt_store.get_settings") as mock_settings:
            mock_settings.return_value.ai.prompt_store_enabled = True
            await preload_prompt_store_cache(db)

        assert _store_cache.get("scaffolder") == "cached content"

    @pytest.mark.asyncio
    async def test_preload_skips_when_disabled(self) -> None:
        """preload_prompt_store_cache is no-op when disabled."""
        db = AsyncMock()
        with patch("app.ai.prompt_store.get_settings") as mock_settings:
            mock_settings.return_value.ai.prompt_store_enabled = False
            await preload_prompt_store_cache(db)
        db.execute.assert_not_called()


# ── Route tests ──


@pytest.fixture
def _auth_developer() -> Generator[None]:
    user = _make_user("developer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _auth_admin() -> Generator[None]:
    user = _make_user("admin")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _auth_viewer() -> Generator[None]:
    user = _make_user("viewer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient]:
    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


@pytest.fixture
def dev_client(_auth_developer: None) -> Generator[TestClient]:
    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


@pytest.fixture
def admin_client(_auth_admin: None) -> Generator[TestClient]:
    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


@pytest.fixture
def viewer_client(_auth_viewer: None) -> Generator[TestClient]:
    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


@pytest.fixture
def _mock_db() -> Generator[AsyncMock]:
    """Override get_db to return a mocked session."""
    db = AsyncMock()
    db.commit = AsyncMock()

    _added_objects: list[object] = []

    def _track_add(obj: object) -> None:
        _added_objects.append(obj)

    db.add = MagicMock(side_effect=_track_add)

    async def _flush_side_effect() -> None:
        """Simulate DB flush — populate auto-generated fields."""
        for obj in _added_objects:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = 1
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = datetime.now(UTC)
        _added_objects.clear()

    db.flush = AsyncMock(side_effect=_flush_side_effect)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield db
    app.dependency_overrides.pop(get_db, None)


class TestPromptRoutes:
    """Route-level tests for prompt store API."""

    def test_unauthenticated_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/v1/prompts")
        assert resp.status_code in (401, 403)

    def test_list_agents_200(self, dev_client: TestClient, _mock_db: AsyncMock) -> None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = ["scaffolder", "dark_mode"]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        _mock_db.execute.return_value = result_mock

        resp = dev_client.get("/api/v1/prompts")
        assert resp.status_code == 200
        assert resp.json()["agents"] == ["scaffolder", "dark_mode"]

    def test_get_active_prompt_200(self, dev_client: TestClient, _mock_db: AsyncMock) -> None:
        template = _make_template(content="scaffolder prompt")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = template
        _mock_db.execute.return_value = result_mock

        resp = dev_client.get("/api/v1/prompts/scaffolder")
        assert resp.status_code == 200
        assert resp.json()["content"] == "scaffolder prompt"

    def test_get_active_prompt_404(self, dev_client: TestClient, _mock_db: AsyncMock) -> None:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        _mock_db.execute.return_value = result_mock

        resp = dev_client.get("/api/v1/prompts/scaffolder")
        assert resp.status_code == 404

    def test_get_active_invalid_agent_404(
        self, dev_client: TestClient, _mock_db: AsyncMock
    ) -> None:
        resp = dev_client.get("/api/v1/prompts/nonexistent_agent")
        assert resp.status_code == 404

    @patch("app.ai.prompt_store_routes.preload_prompt_store_cache", new_callable=AsyncMock)
    def test_create_prompt_201(
        self,
        mock_preload: AsyncMock,
        admin_client: TestClient,
        _mock_db: AsyncMock,
    ) -> None:
        # create: version query returns 0
        version_result = MagicMock()
        version_result.scalar_one.return_value = 0
        _mock_db.execute.return_value = version_result

        resp = admin_client.post(
            "/api/v1/prompts",
            json={
                "agent_id": "scaffolder",
                "content": "new prompt content",
                "description": "test version",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_id"] == "scaffolder"
        assert data["version"] == 1

    @patch("app.ai.prompt_store_routes.preload_prompt_store_cache", new_callable=AsyncMock)
    def test_create_prompt_403_non_admin(
        self,
        mock_preload: AsyncMock,
        dev_client: TestClient,
        _mock_db: AsyncMock,
    ) -> None:
        resp = dev_client.post(
            "/api/v1/prompts",
            json={"agent_id": "scaffolder", "content": "new prompt"},
        )
        assert resp.status_code == 403

    def test_create_prompt_invalid_agent_404(
        self, admin_client: TestClient, _mock_db: AsyncMock
    ) -> None:
        resp = admin_client.post(
            "/api/v1/prompts",
            json={"agent_id": "nonexistent", "content": "content"},
        )
        assert resp.status_code == 404

    @patch("app.ai.prompt_store_routes.preload_prompt_store_cache", new_callable=AsyncMock)
    def test_activate_prompt_200(
        self,
        mock_preload: AsyncMock,
        admin_client: TestClient,
        _mock_db: AsyncMock,
    ) -> None:
        template = _make_template(id=5, active=True)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = template
        _mock_db.execute.return_value = result_mock

        resp = admin_client.post(
            "/api/v1/prompts/activate",
            json={"template_id": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    @patch("app.ai.prompt_store_routes.preload_prompt_store_cache", new_callable=AsyncMock)
    def test_activate_prompt_404(
        self,
        mock_preload: AsyncMock,
        admin_client: TestClient,
        _mock_db: AsyncMock,
    ) -> None:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        _mock_db.execute.return_value = result_mock

        resp = admin_client.post(
            "/api/v1/prompts/activate",
            json={"template_id": 999},
        )
        assert resp.status_code == 404

    @patch("app.ai.prompt_store_routes.preload_prompt_store_cache", new_callable=AsyncMock)
    def test_rollback_200(
        self,
        mock_preload: AsyncMock,
        admin_client: TestClient,
        _mock_db: AsyncMock,
    ) -> None:
        # get_active returns v2
        active_v2 = _make_template(version=2, active=True)
        # rollback finds v1, then activates it
        v1 = _make_template(id=10, version=1, active=False)

        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            if call_count == 1:
                r.scalar_one_or_none.return_value = active_v2
            elif call_count == 2:
                r.scalar_one_or_none.return_value = v1
            else:
                r.scalar_one_or_none.return_value = v1
            return r

        _mock_db.execute = AsyncMock(side_effect=side_effect)

        resp = admin_client.post("/api/v1/prompts/scaffolder/rollback")
        assert resp.status_code == 200

    @patch("app.ai.prompt_store_routes.preload_prompt_store_cache", new_callable=AsyncMock)
    def test_rollback_404_no_previous(
        self,
        mock_preload: AsyncMock,
        admin_client: TestClient,
        _mock_db: AsyncMock,
    ) -> None:
        # get_active returns v1 → can't rollback
        active_v1 = _make_template(version=1, active=True)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = active_v1
        _mock_db.execute.return_value = result_mock

        resp = admin_client.post("/api/v1/prompts/scaffolder/rollback")
        assert resp.status_code == 404

    @patch("app.ai.prompt_store_routes.preload_prompt_store_cache", new_callable=AsyncMock)
    def test_seed_200(
        self,
        mock_preload: AsyncMock,
        admin_client: TestClient,
        _mock_db: AsyncMock,
    ) -> None:
        with patch.object(
            PromptStoreService,
            "seed_from_skill_files",
            new_callable=AsyncMock,
            return_value={"scaffolder": 1, "dark_mode": 1},
        ):
            resp = admin_client.post("/api/v1/prompts/seed")
        assert resp.status_code == 200
        assert resp.json()["seeded"]["scaffolder"] == 1

    def test_list_versions_200(self, dev_client: TestClient, _mock_db: AsyncMock) -> None:
        templates = [_make_template(version=2), _make_template(version=1)]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = templates
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        _mock_db.execute.return_value = result_mock

        resp = dev_client.get("/api/v1/prompts/scaffolder/versions")
        assert resp.status_code == 200
        assert len(resp.json()["templates"]) == 2

    def test_viewer_cannot_access(self, viewer_client: TestClient, _mock_db: AsyncMock) -> None:
        resp = viewer_client.get("/api/v1/prompts")
        assert resp.status_code == 403
