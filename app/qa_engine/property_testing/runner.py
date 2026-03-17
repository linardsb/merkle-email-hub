"""Property test runner — generates emails, checks invariants, reports failures."""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.core.exceptions import DomainValidationError
from app.core.logging import get_logger
from app.qa_engine.property_testing.generators import EmailConfig, build_email, random_email_config
from app.qa_engine.property_testing.invariants import ALL_INVARIANTS, InvariantResult

logger = get_logger(__name__)


@dataclass(frozen=True)
class PropertyFailure:
    """A single invariant failure with the config that caused it."""

    invariant_name: str
    violations: tuple[str, ...]
    config: EmailConfig


@dataclass(frozen=True)
class PropertyTestReport:
    """Results of a property test run."""

    total_cases: int
    passed: int
    failed: int
    failures: tuple[PropertyFailure, ...] = ()
    seed: int = 0


class PropertyTestRunner:
    """Generates random emails and checks invariants."""

    async def run(
        self,
        invariant_names: list[str] | None = None,
        num_cases: int = 100,
        seed: int | None = None,
    ) -> PropertyTestReport:
        """Run property tests.

        Args:
            invariant_names: Invariants to check. None = all.
            num_cases: Number of random emails to generate.
            seed: Fixed seed for reproducibility. None = random.

        Returns:
            PropertyTestReport with failures and minimal configs.
        """
        actual_seed = seed if seed is not None else random.randint(0, 2**32 - 1)

        # Resolve invariants
        if invariant_names:
            unknown = [n for n in invariant_names if n not in ALL_INVARIANTS]
            if unknown:
                raise DomainValidationError(f"Unknown invariants: {', '.join(unknown)}")
            invariants = [ALL_INVARIANTS[n] for n in invariant_names]
        else:
            invariants = list(ALL_INVARIANTS.values())

        if not invariants:
            return PropertyTestReport(total_cases=0, passed=0, failed=0, seed=actual_seed)

        # Generate configs deterministically using seeded RNG
        rng = random.Random(actual_seed)
        configs: list[EmailConfig] = [random_email_config(rng) for _ in range(num_cases)]

        # Check invariants
        failures: list[PropertyFailure] = []
        passed_count = 0
        failed_count = 0

        for config in configs:
            html = build_email(config)
            case_failed = False

            for invariant in invariants:
                try:
                    result: InvariantResult = invariant.check(html)
                except Exception as exc:
                    logger.warning(
                        "property_test.invariant_error",
                        invariant=invariant.name,
                        error=str(exc),
                    )
                    continue

                if not result.passed:
                    case_failed = True
                    failures.append(
                        PropertyFailure(
                            invariant_name=invariant.name,
                            violations=result.violations,
                            config=config,
                        )
                    )

            if case_failed:
                failed_count += 1
            else:
                passed_count += 1

        logger.info(
            "property_test.completed",
            total=len(configs),
            passed=passed_count,
            failed=failed_count,
            unique_invariant_failures=len({f.invariant_name for f in failures}),
            seed=actual_seed,
        )

        return PropertyTestReport(
            total_cases=len(configs),
            passed=passed_count,
            failed=failed_count,
            failures=tuple(failures),
            seed=actual_seed,
        )
