"""Compile Maizzle source templates to production HTML.

Uses the maizzle-builder sidecar (services/maizzle-builder) to compile
templates. Caches compiled HTML in library/ directory.
"""

from pathlib import Path

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

MAIZZLE_BUILDER_URL = "http://localhost:3001"
MAIZZLE_SRC_DIR = Path(__file__).parent / "maizzle_src"
LIBRARY_DIR = Path(__file__).parent / "library"


async def compile_template(name: str) -> str:
    """Compile a single Maizzle source template to production HTML.

    Args:
        name: Template name (without .html extension).

    Returns:
        Compiled HTML string.
    """
    source_path = MAIZZLE_SRC_DIR / f"{name}.html"
    source = source_path.read_text()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{MAIZZLE_BUILDER_URL}/build",
            json={"source": source, "options": {"inlineCSS": True}},
        )
        response.raise_for_status()
        compiled: str = response.json()["html"]

    output_path = LIBRARY_DIR / f"{name}.html"
    output_path.write_text(compiled)
    logger.info("templates.compile_completed", template=name, size=len(compiled))
    return compiled


async def compile_all() -> dict[str, str]:
    """Compile all Maizzle source templates. Returns {name: html}."""
    results: dict[str, str] = {}
    for source_file in sorted(MAIZZLE_SRC_DIR.glob("*.html")):
        name = source_file.stem
        results[name] = await compile_template(name)
    return results
