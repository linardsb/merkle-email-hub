"""Tests for the scheduling job registry."""

import pytest

from app.core.exceptions import DomainValidationError, NotFoundError
from app.scheduling.registry import (
    get_job_callable,
    get_registry,
    scheduled_job,
)


class TestScheduledJobDecorator:
    def test_registers_with_correct_cron(self) -> None:
        """Decorator registers the function with its cron expression."""

        @scheduled_job(cron="0 */6 * * *")
        async def my_task() -> None:
            pass

        registry = get_registry()
        assert "my_task" in registry
        callable_fn, cron = registry["my_task"]
        assert cron == "0 */6 * * *"
        assert callable_fn is my_task

    def test_invalid_cron_raises(self) -> None:
        """Invalid cron expression raises DomainValidationError at registration."""
        with pytest.raises(DomainValidationError, match="Invalid cron expression"):

            @scheduled_job(cron="not-a-cron")
            async def bad_task() -> None:
                pass

    def test_get_job_callable_not_found(self) -> None:
        """Looking up a non-existent job raises NotFoundError."""
        with pytest.raises(NotFoundError, match="No scheduled job registered"):
            get_job_callable("does_not_exist")
