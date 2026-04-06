#!/usr/bin/env bash
# Scaffold a new vertical slice feature under app/{name}/.
# Usage: bash scripts/scaffold-feature.sh <feature_name>
#
# Generates: __init__.py, models.py, schemas.py, exceptions.py,
#            repository.py, service.py, routes.py,
#            tests/__init__.py, tests/conftest.py, tests/test_service.py
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <feature_name>"
    echo "  feature_name: lowercase, underscores only (e.g. billing, campaign_analytics)"
    exit 1
fi

FEATURE="$1"

# Validate: lowercase letters and underscores only
if [[ ! "$FEATURE" =~ ^[a-z][a-z0-9_]*$ ]]; then
    echo "Error: feature name must be lowercase letters, digits, and underscores (start with letter)."
    echo "  Got: '$FEATURE'"
    exit 1
fi

FEATURE_DIR="app/$FEATURE"

if [[ -d "$FEATURE_DIR" ]]; then
    echo "Error: directory '$FEATURE_DIR' already exists. Aborting."
    exit 1
fi

# Derive PascalCase class name: billing_report -> BillingReport
pascal_case() {
    echo "$1" | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1' | sed 's/ //g'
}

CLASS=$(pascal_case "$FEATURE")

echo "Scaffolding vertical slice: $FEATURE_DIR (class prefix: $CLASS)"

mkdir -p "$FEATURE_DIR/tests"

# --- __init__.py ---
cat > "$FEATURE_DIR/__init__.py" << 'EOF'
EOF

# --- models.py ---
cat > "$FEATURE_DIR/models.py" << PYEOF
"""${CLASS} database models."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import SoftDeleteMixin, TimestampMixin


class ${CLASS}(Base, TimestampMixin, SoftDeleteMixin):
    """${CLASS} model."""

    __tablename__ = "${FEATURE}s"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
PYEOF

# --- schemas.py ---
cat > "$FEATURE_DIR/schemas.py" << PYEOF
"""Pydantic schemas for the ${FEATURE} feature."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ${CLASS}Base(BaseModel):
    """Shared ${FEATURE} attributes."""

    name: str = Field(..., min_length=1, max_length=200, description="Name")


class ${CLASS}Create(${CLASS}Base):
    """Schema for creating a ${FEATURE}."""


class ${CLASS}Update(BaseModel):
    """Schema for updating a ${FEATURE}. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=200)


class ${CLASS}Response(${CLASS}Base):
    """Schema for ${FEATURE} responses."""

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
PYEOF

# --- exceptions.py ---
cat > "$FEATURE_DIR/exceptions.py" << PYEOF
"""Feature-specific exceptions for ${FEATURE} management."""

from app.core.exceptions import DomainValidationError, NotFoundError


class ${CLASS}NotFoundError(NotFoundError):
    """Raised when a ${FEATURE} is not found by ID."""


class ${CLASS}AlreadyExistsError(DomainValidationError):
    """Raised when creating a ${FEATURE} with a duplicate name."""
PYEOF

# --- repository.py ---
cat > "$FEATURE_DIR/repository.py" << PYEOF
"""Data access layer for ${FEATURE} management."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.${FEATURE}.models import ${CLASS}
from app.${FEATURE}.schemas import ${CLASS}Create
from app.shared.utils import escape_like


class ${CLASS}Repository:
    """Database operations for ${FEATURE}s."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, ${FEATURE}_id: int) -> ${CLASS} | None:
        result = await self.db.execute(
            select(${CLASS}).where(${CLASS}.id == ${FEATURE}_id, ${CLASS}.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> ${CLASS} | None:
        result = await self.db.execute(
            select(${CLASS}).where(${CLASS}.name == name, ${CLASS}.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> list[${CLASS}]:
        query = select(${CLASS}).where(${CLASS}.deleted_at.is_(None))
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(${CLASS}.name.ilike(pattern))
        query = query.order_by(${CLASS}.name).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, *, search: str | None = None) -> int:
        query = select(func.count()).select_from(${CLASS}).where(${CLASS}.deleted_at.is_(None))
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(${CLASS}.name.ilike(pattern))
        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, data: ${CLASS}Create) -> ${CLASS}:
        item = ${CLASS}(**data.model_dump())
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item
PYEOF

# --- service.py ---
cat > "$FEATURE_DIR/service.py" << PYEOF
"""Business logic for ${FEATURE} management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.${FEATURE}.exceptions import ${CLASS}AlreadyExistsError, ${CLASS}NotFoundError
from app.${FEATURE}.repository import ${CLASS}Repository
from app.${FEATURE}.schemas import ${CLASS}Create, ${CLASS}Response
from app.shared.schemas import PaginatedResponse, PaginationParams

logger = get_logger(__name__)


class ${CLASS}Service:
    """Business logic for ${FEATURE} management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ${CLASS}Repository(db)

    async def get(self, ${FEATURE}_id: int) -> ${CLASS}Response:
        logger.info("${FEATURE}.fetch_started", ${FEATURE}_id=${FEATURE}_id)
        item = await self.repository.get(${FEATURE}_id)
        if not item:
            raise ${CLASS}NotFoundError(f"${CLASS} {${FEATURE}_id} not found")
        return ${CLASS}Response.model_validate(item)

    async def list(
        self,
        pagination: PaginationParams,
        *,
        search: str | None = None,
    ) -> PaginatedResponse[${CLASS}Response]:
        logger.info("${FEATURE}.list_started", page=pagination.page)
        items = await self.repository.list(
            offset=pagination.offset,
            limit=pagination.page_size,
            search=search,
        )
        total = await self.repository.count(search=search)
        return PaginatedResponse[${CLASS}Response](
            items=[${CLASS}Response.model_validate(i) for i in items],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def create(self, data: ${CLASS}Create) -> ${CLASS}Response:
        logger.info("${FEATURE}.create_started", name=data.name)
        existing = await self.repository.get_by_name(data.name)
        if existing:
            raise ${CLASS}AlreadyExistsError(
                f"${CLASS} with name '{data.name}' already exists"
            )
        item = await self.repository.create(data)
        logger.info("${FEATURE}.create_completed", ${FEATURE}_id=item.id)
        return ${CLASS}Response.model_validate(item)
PYEOF

# --- routes.py ---
cat > "$FEATURE_DIR/routes.py" << PYEOF
# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for ${FEATURE} management."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.${FEATURE}.schemas import ${CLASS}Create, ${CLASS}Response
from app.${FEATURE}.service import ${CLASS}Service
from app.shared.schemas import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/v1/${FEATURE}s", tags=["${FEATURE}s"])


def get_service(db: AsyncSession = Depends(get_db)) -> ${CLASS}Service:
    """Dependency to create ${CLASS}Service with request-scoped session."""
    return ${CLASS}Service(db)


@router.get("/", response_model=PaginatedResponse[${CLASS}Response])
@limiter.limit("30/minute")
async def list_${FEATURE}s(
    request: Request,
    pagination: PaginationParams = Depends(),
    search: str | None = Query(None, max_length=200),
    service: ${CLASS}Service = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> PaginatedResponse[${CLASS}Response]:
    """List ${FEATURE}s with pagination."""
    _ = request
    return await service.list(pagination, search=search)


@router.get("/{${FEATURE}_id}", response_model=${CLASS}Response)
@limiter.limit("30/minute")
async def get_${FEATURE}(
    request: Request,
    ${FEATURE}_id: int,
    service: ${CLASS}Service = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> ${CLASS}Response:
    """Get a ${FEATURE} by ID."""
    _ = request
    return await service.get(${FEATURE}_id)


@router.post("/", response_model=${CLASS}Response, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_${FEATURE}(
    request: Request,
    data: ${CLASS}Create,
    service: ${CLASS}Service = Depends(get_service),
    _current_user: User = Depends(require_role("admin")),
) -> ${CLASS}Response:
    """Create a new ${FEATURE}."""
    _ = request
    return await service.create(data)
PYEOF

# --- tests/__init__.py ---
cat > "$FEATURE_DIR/tests/__init__.py" << 'EOF'
EOF

# --- tests/conftest.py ---
cat > "$FEATURE_DIR/tests/conftest.py" << PYEOF
"""Shared test fixtures for the ${FEATURE} feature."""

from unittest.mock import AsyncMock

import pytest

from app.${FEATURE}.models import ${CLASS}
from app.shared.models import utcnow


def make_${FEATURE}(**overrides: object) -> ${CLASS}:
    """Factory to create a ${CLASS} instance with sensible defaults."""
    now = utcnow()
    defaults: dict[str, object] = {
        "id": 1,
        "name": "Test ${CLASS}",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return ${CLASS}(**defaults)


@pytest.fixture
def sample_${FEATURE}() -> ${CLASS}:
    """A single default ${FEATURE} instance."""
    return make_${FEATURE}()


@pytest.fixture
def sample_${FEATURE}s() -> list[${CLASS}]:
    """Multiple ${FEATURE} instances for list tests."""
    return [
        make_${FEATURE}(id=1, name="Alpha"),
        make_${FEATURE}(id=2, name="Beta"),
        make_${FEATURE}(id=3, name="Gamma"),
    ]


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock AsyncSession for repository tests."""
    return AsyncMock()
PYEOF

# --- tests/test_service.py ---
cat > "$FEATURE_DIR/tests/test_service.py" << PYEOF
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Unit tests for ${CLASS}Service business logic."""

from unittest.mock import AsyncMock

import pytest

from app.${FEATURE}.exceptions import ${CLASS}AlreadyExistsError, ${CLASS}NotFoundError
from app.${FEATURE}.schemas import ${CLASS}Create
from app.${FEATURE}.service import ${CLASS}Service
from app.${FEATURE}.tests.conftest import make_${FEATURE}
from app.shared.schemas import PaginationParams


@pytest.fixture
def service() -> ${CLASS}Service:
    mock_db = AsyncMock()
    svc = ${CLASS}Service(mock_db)
    svc.repository = AsyncMock()
    return svc


async def test_get_success(service):
    item = make_${FEATURE}(id=1, name="Test")
    service.repository.get = AsyncMock(return_value=item)
    result = await service.get(1)
    assert result.id == 1
    assert result.name == "Test"
    service.repository.get.assert_awaited_once_with(1)


async def test_get_not_found(service):
    service.repository.get = AsyncMock(return_value=None)
    with pytest.raises(${CLASS}NotFoundError, match="not found"):
        await service.get(999)


async def test_list(service):
    items = [make_${FEATURE}(id=1, name="A"), make_${FEATURE}(id=2, name="B")]
    service.repository.list = AsyncMock(return_value=items)
    service.repository.count = AsyncMock(return_value=2)
    result = await service.list(PaginationParams(page=1, page_size=20))
    assert len(result.items) == 2
    assert result.total == 2


async def test_create_success(service):
    data = ${CLASS}Create(name="New")
    created = make_${FEATURE}(id=10, name="New")
    service.repository.get_by_name = AsyncMock(return_value=None)
    service.repository.create = AsyncMock(return_value=created)
    result = await service.create(data)
    assert result.id == 10


async def test_create_duplicate(service):
    data = ${CLASS}Create(name="Exists")
    existing = make_${FEATURE}(id=1, name="Exists")
    service.repository.get_by_name = AsyncMock(return_value=existing)
    with pytest.raises(${CLASS}AlreadyExistsError, match="already exists"):
        await service.create(data)
PYEOF

# Auto-format and fix import ordering
uv run ruff format "$FEATURE_DIR/" --quiet 2>/dev/null || true
uv run ruff check --fix "$FEATURE_DIR/" --quiet 2>/dev/null || true

echo ""
echo "Created vertical slice: $FEATURE_DIR/"
echo "  __init__.py, models.py, schemas.py, exceptions.py,"
echo "  repository.py, service.py, routes.py,"
echo "  tests/__init__.py, tests/conftest.py, tests/test_service.py"
echo ""
echo "Next steps:"
echo "  1. Edit models.py to add your domain-specific columns"
echo "  2. Update schemas.py to match your model fields"
echo "  3. Register routes in app/main.py:"
echo "       from app.${FEATURE}.routes import router as ${FEATURE}_router"
echo "       app.include_router(${FEATURE}_router)"
echo "  4. Create migration: make db-revision m=\"add ${FEATURE} tables\""
echo "  5. Run migration: make db-migrate"
echo "  6. Verify: make check"
