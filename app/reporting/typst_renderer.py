"""Typst CLI subprocess wrapper for PDF compilation."""

from __future__ import annotations

import asyncio
import json
import re
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.reporting.exceptions import ReportTooLargeError, TypstCompilationError

logger = get_logger(__name__)

# Templates directory (sibling to this file)
TEMPLATES_DIR = Path(__file__).parent / "templates"


class TypstRenderer:
    """Compile Typst templates with data into PDF bytes."""

    async def render(self, template_name: str, data: dict[str, object]) -> bytes:
        """Compile a Typst template with JSON data to PDF.

        Args:
            template_name: Name of .typ file in templates/ (e.g. "qa_report")
            data: Template data, serialized to JSON and loaded by the template

        Returns:
            PDF file bytes

        Raises:
            TypstCompilationError: If Typst CLI fails
            ReportTooLargeError: If output exceeds max size
        """
        settings = get_settings()
        typst_bin = settings.reporting.typst_binary
        # Validate binary name — only allow simple names or absolute paths
        if not re.match(r"^[a-zA-Z0-9_-]+$", typst_bin) and not Path(typst_bin).is_absolute():
            raise TypstCompilationError(f"Invalid typst binary path: {typst_bin}")
        timeout_s = settings.reporting.compilation_timeout_s
        max_size = settings.reporting.max_report_size_mb * 1024 * 1024

        template_path = TEMPLATES_DIR / f"{template_name}.typ"
        if not template_path.exists():
            raise TypstCompilationError(f"Template not found: {template_name}")

        with tempfile.TemporaryDirectory(prefix="typst_report_") as tmpdir:
            work_dir = Path(tmpdir)

            # Write data JSON for the template to import
            data_path = work_dir / "data.json"
            data_path.write_text(json.dumps(data, default=str), encoding="utf-8")

            # Copy template to work dir (so relative imports resolve)
            input_path = work_dir / f"{template_name}.typ"
            input_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

            output_path = work_dir / "output.pdf"

            cmd = [
                typst_bin,
                "compile",
                str(input_path),
                str(output_path),
            ]

            logger.info(
                "typst.compilation_started",
                template=template_name,
                data_keys=list(data.keys()),
            )

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
            )
            try:
                _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
            except TimeoutError as exc:
                proc.kill()
                raise TypstCompilationError(
                    f"Typst compilation timed out after {timeout_s}s"
                ) from exc

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()[:500]
                raise TypstCompilationError(f"Typst compilation failed: {error_msg}")

            if not output_path.exists():
                raise TypstCompilationError("Typst produced no output file")

            pdf_bytes = output_path.read_bytes()

            if len(pdf_bytes) > max_size:
                raise ReportTooLargeError(
                    f"Report size {len(pdf_bytes)} bytes exceeds limit "
                    f"{settings.reporting.max_report_size_mb}MB"
                )

            logger.info(
                "typst.compilation_completed",
                template=template_name,
                pdf_size_bytes=len(pdf_bytes),
            )
            return pdf_bytes
