# CLAUDE.md

## Project Overview

Centralised email development platform with AI-powered agents. Built with **vertical slice architecture** — FastAPI backend, Next.js 16 frontend, PostgreSQL + Redis infrastructure. Python 3.12+, strict type checking with MyPy and Pyright.

## Core Principles

**Vertical Slice Architecture** — Each feature owns its models, schemas, routes, and business logic under `app/{feature}/`. Shared utilities go in `app/shared/` only when used by 3+ features. Core infrastructure in `app/core/`.

**Type Safety (CRITICAL)** — Strict MyPy + Pyright enforced. All functions must have complete type annotations. No `Any` without justification.

**Structured Logging** — `domain.component.action_state` pattern via structlog. Logger: `from app.core.logging import get_logger`.

## Essential Commands

```bash
# Local development
make db              # Start PostgreSQL + Redis (Docker)
make dev             # Start backend (:8891) + frontend (:3000)
make dev-be          # Backend only
make dev-fe          # Frontend only

# Quality checks
make check           # All checks (lint + types + tests)
make test            # Unit tests
make lint            # Format + lint (ruff)
make types           # mypy + pyright

# Database
make db-migrate      # Run migrations
make db-revision m="description"  # Create new migration

# Docker
make docker          # Full stack (port :80)
make docker-down     # Stop all services
```

## Architecture

### Project Structure

```
merkle-email-hub/
├── app/                # Backend features (VSA)
│   ├── core/           # Infrastructure (config, database, logging, middleware, health, rate_limit, redis)
│   ├── shared/         # Cross-feature utilities (pagination, timestamps, error schemas)
│   ├── auth/           # JWT auth + RBAC + user management
│   ├── example/        # Reference VSA feature ("Items" CRUD)

│   ├── ai/             # AI layer (protocol interfaces, provider registry, chat API)


│   ├── knowledge/      # RAG pipeline (pgvector, document processing, hybrid search)


│   ├── streaming/      # WebSocket streaming (Pub/Sub, connection manager)

│   └── tests/          # Integration tests
├── cms/               # Frontend monorepo (Next.js 16 + React 19)
├── alembic/           # Database migrations
├── .claude/           # AI-assisted development commands + rules
├── nginx/             # Reverse proxy
└── pyproject.toml     # Dependencies, tooling config
```

### Database

- **Async SQLAlchemy** with configurable connection pooling
- Base class: `app.core.database.Base`
- Session: `get_db()` from `app.core.database`; standalone: `get_db_context()`
- All models inherit `TimestampMixin` from `app.shared.models`

### Configuration

Nested Pydantic settings with `env_nested_delimiter="__"`:
- `DATABASE__URL`, `DATABASE__POOL_SIZE`
- `REDIS__URL`
- `AUTH__JWT_SECRET_KEY`, `AUTH__ACCESS_TOKEN_EXPIRE_MINUTES`

- `AI__PROVIDER`, `AI__MODEL`, `AI__API_KEY`


### Shared Utilities

- **Pagination**: `PaginationParams` + `PaginatedResponse[T]` from `app.shared.schemas`
- **Timestamps**: `TimestampMixin` + `utcnow()` from `app.shared.models`
- **Errors**: `AppError` hierarchy in `app.core.exceptions`
- **SQL Escaping**: `escape_like()` from `app.shared.utils`

## Development Guidelines

**Feature file order:** schemas → models → repository → service → exceptions → routes → tests

**Layer responsibilities:**
- **Routes** → HTTP concerns (status codes, dependency injection) — thin, delegate to service
- **Service** → Business logic, validation, logging, orchestration
- **Repository** → Database operations only (no business logic)
- **Exceptions** → Inherit from `AppError` for automatic HTTP status mapping

**Roles:** admin,developer,viewer

## Compact instructions

When compacting, preserve:
- Current task context and active plan file path
- List of all files modified in this session
- Test commands run and their results
- Key decisions made during this session
