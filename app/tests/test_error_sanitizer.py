"""Tests for error message sanitization."""

from app.core.error_sanitizer import get_safe_error_message, get_safe_error_type
from app.core.exceptions import (
    AppError,
    ConflictError,
    DomainValidationError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)


class TestGetSafeErrorMessage:
    """Verify internal details are never returned to clients."""

    def test_not_found_returns_generic(self) -> None:
        exc = NotFoundError("User id=42 in org_id=7 not found")
        assert get_safe_error_message(exc) == "Resource not found"

    def test_forbidden_returns_generic(self) -> None:
        exc = ForbiddenError("User 5 not member of project 12")
        assert get_safe_error_message(exc) == "Access denied"

    def test_service_unavailable_returns_generic(self) -> None:
        exc = ServiceUnavailableError("Cannot connect to postgres://prod-db:5432")
        assert get_safe_error_message(exc) == "Service temporarily unavailable"

    def test_validation_error_passes_through(self) -> None:
        exc = DomainValidationError("Name must be at least 3 characters")
        assert get_safe_error_message(exc) == "Name must be at least 3 characters"

    def test_unknown_exception_returns_generic(self) -> None:
        exc = RuntimeError("segfault at 0xDEADBEEF")
        assert get_safe_error_message(exc) == "An unexpected error occurred"

    def test_app_error_base_returns_generic(self) -> None:
        exc = AppError("Internal: pool_size=10 exceeded")
        assert "pool_size" not in get_safe_error_message(exc)

    def test_ai_execution_error_hides_provider_details(self) -> None:
        from app.ai.exceptions import AIExecutionError

        exc = AIExecutionError("Anthropic rate limit: 429 Too Many Requests")
        assert "Anthropic" not in get_safe_error_message(exc)
        assert "429" not in get_safe_error_message(exc)

    def test_build_failed_hides_sidecar_url(self) -> None:
        from app.email_engine.exceptions import BuildFailedError

        exc = BuildFailedError("Cannot connect to http://maizzle-builder:3001")
        assert "maizzle-builder" not in get_safe_error_message(exc)
        assert "3001" not in get_safe_error_message(exc)

    def test_conflict_error_returns_generic(self) -> None:
        exc = ConflictError("Duplicate entry for key 'email' = 'admin@test.com'")
        assert "admin@test.com" not in get_safe_error_message(exc)
        assert get_safe_error_message(exc) == "Resource conflict"

    def test_project_access_denied_returns_generic(self) -> None:
        from app.projects.exceptions import ProjectAccessDeniedError

        exc = ProjectAccessDeniedError("User 5 not member of project 12")
        assert get_safe_error_message(exc) == "Access denied"

    def test_blueprint_node_error_hides_details(self) -> None:
        from app.ai.blueprints.exceptions import BlueprintNodeError

        exc = BlueprintNodeError("scaffolder", "Anthropic API rate_limit_exceeded")
        assert "Anthropic" not in get_safe_error_message(exc)
        assert get_safe_error_message(exc) == "Blueprint step failed"

    def test_export_failed_hides_details(self) -> None:
        from app.connectors.exceptions import ExportFailedError

        exc = ExportFailedError("Braze API key invalid: sk-xxx-123")
        assert "sk-xxx" not in get_safe_error_message(exc)
        assert get_safe_error_message(exc) == "Export operation failed"


class TestGetSafeErrorType:
    """Verify internal class names are never returned."""

    def test_not_found(self) -> None:
        assert get_safe_error_type(NotFoundError("x")) == "not_found"

    def test_validation(self) -> None:
        assert get_safe_error_type(DomainValidationError("x")) == "validation_error"

    def test_forbidden(self) -> None:
        assert get_safe_error_type(ForbiddenError("x")) == "forbidden"

    def test_conflict(self) -> None:
        assert get_safe_error_type(ConflictError("x")) == "conflict"

    def test_service_unavailable(self) -> None:
        assert get_safe_error_type(ServiceUnavailableError("x")) == "service_unavailable"

    def test_unknown_returns_server_error(self) -> None:
        assert get_safe_error_type(RuntimeError("x")) == "server_error"

    def test_ai_error_returns_ai_error(self) -> None:
        from app.ai.exceptions import AIExecutionError

        assert get_safe_error_type(AIExecutionError("x")) == "ai_error"

    def test_blueprint_error_returns_ai_error(self) -> None:
        from app.ai.blueprints.exceptions import BlueprintNodeError

        assert get_safe_error_type(BlueprintNodeError("node", "err")) == "ai_error"

    def test_subclass_inherits_parent_type(self) -> None:
        """ProjectAccessDeniedError inherits ForbiddenError -> 'forbidden'."""
        from app.projects.exceptions import ProjectAccessDeniedError

        assert get_safe_error_type(ProjectAccessDeniedError("x")) == "forbidden"

    def test_invalid_credentials_returns_authentication_error(self) -> None:
        from app.auth.exceptions import InvalidCredentialsError

        assert get_safe_error_type(InvalidCredentialsError("x")) == "authentication_error"

    def test_account_locked_returns_account_locked(self) -> None:
        from app.auth.exceptions import AccountLockedError

        assert get_safe_error_type(AccountLockedError("x")) == "account_locked"
