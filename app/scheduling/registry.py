"""Job registry for the scheduling engine.

Provides the ``@scheduled_job`` decorator that registers async callables
with a default cron expression.  The registry is a module-level dict
consulted by :class:`CronScheduler` at startup.
"""

from collections.abc import Awaitable, Callable

from croniter import croniter

from app.core.exceptions import DomainValidationError, NotFoundError

# name → (callable, default_cron)
_JOB_REGISTRY: dict[str, tuple[Callable[..., Awaitable[None]], str]] = {}


def scheduled_job(
    cron: str,
) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]:
    """Register an async callable as a scheduled job.

    Args:
        cron: Default cron expression (validated at registration time).

    Raises:
        DomainValidationError: If the cron expression is invalid.
    """
    if not croniter.is_valid(cron):
        msg = f"Invalid cron expression: {cron!r}"
        raise DomainValidationError(msg)

    def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        _JOB_REGISTRY[func.__name__] = (func, cron)
        return func

    return decorator


def get_registry() -> dict[str, tuple[Callable[..., Awaitable[None]], str]]:
    """Return an immutable snapshot of the job registry."""
    return dict(_JOB_REGISTRY)


def get_job_callable(name: str) -> Callable[..., Awaitable[None]]:
    """Look up a registered callable by name.

    Raises:
        NotFoundError: If no job is registered with *name*.
    """
    entry = _JOB_REGISTRY.get(name)
    if entry is None:
        msg = f"No scheduled job registered with name {name!r}"
        raise NotFoundError(msg)
    return entry[0]


def clear_registry() -> None:
    """Remove all registered jobs (used in tests)."""
    _JOB_REGISTRY.clear()
