#!/usr/bin/env python3
"""Cross-reference email-client-matrix.yaml with ontology CSS support data.

Compares the centralized client matrix against the ontology registry to
detect drift — cases where the matrix says a property is unsupported but
the ontology (synced from CanIEmail) says it is.

Usage:
    uv run python scripts/sync-client-matrix.py --check
    uv run python scripts/sync-client-matrix.py --check --verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.knowledge.client_matrix import SupportLevel as MatrixSupport
from app.knowledge.client_matrix import load_client_matrix
from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.types import SupportLevel as OntologySupport

# Map ontology client IDs to matrix client IDs where they differ
_ONTOLOGY_TO_MATRIX: dict[str, str] = {
    # Most IDs match; add overrides here if needed
}


def _ontology_to_matrix_id(ontology_id: str) -> str:
    return _ONTOLOGY_TO_MATRIX.get(ontology_id, ontology_id)


def check_drift(*, verbose: bool = False) -> list[str]:
    """Compare matrix CSS support with ontology and return drift warnings."""
    matrix = load_client_matrix()
    ontology = load_ontology()
    warnings: list[str] = []

    for profile in matrix.clients:
        matrix_id = profile.id
        ontology_id = matrix_id  # Same in our system

        ontology_client = ontology.get_client(ontology_id)
        if not ontology_client:
            if verbose:
                print(f"  [skip] {matrix_id}: not in ontology")
            continue

        # Check each CSS property in the matrix against ontology
        for category, props in profile.css_support.items():
            for prop_name, css_support in props.items():
                # Try to find this property in ontology (property IDs use underscores)
                prop_id = prop_name.replace("-", "_")
                ontology_entry = ontology.get_support_entry(prop_id, ontology_id)
                if ontology_entry is None:
                    continue

                matrix_level = css_support.support
                ontology_level = ontology_entry.level

                # Drift: matrix says NONE but ontology says PARTIAL or FULL
                if matrix_level == MatrixSupport.NONE and ontology_level in (
                    OntologySupport.PARTIAL,
                    OntologySupport.FULL,
                ):
                    msg = (
                        f"[drift] {matrix_id}/{category}/{prop_name}: "
                        f"matrix=NONE but ontology={ontology_level.value}"
                    )
                    warnings.append(msg)
                    if verbose:
                        print(f"  {msg}")

                # Reverse drift: matrix says FULL but ontology says NONE
                if matrix_level == MatrixSupport.FULL and ontology_level == OntologySupport.NONE:
                    msg = (
                        f"[drift] {matrix_id}/{category}/{prop_name}: matrix=FULL but ontology=NONE"
                    )
                    warnings.append(msg)
                    if verbose:
                        print(f"  {msg}")

    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-reference client matrix with ontology CSS support data.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for drift between matrix and ontology",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )
    args = parser.parse_args()

    if not args.check:
        parser.print_help()
        return

    print("Checking client matrix vs ontology drift...")
    load_client_matrix.cache_clear()
    load_ontology.cache_clear()

    warnings = check_drift(verbose=args.verbose)

    if warnings:
        print(f"\n{len(warnings)} drift warning(s) found:")
        for w in warnings:
            print(f"  {w}")
        print(
            "\nDrift in CSS support entries may indicate the matrix needs "
            "updating after an ontology sync. Review manually before applying."
        )
    else:
        print("No drift detected. Matrix is consistent with ontology.")


if __name__ == "__main__":
    main()
