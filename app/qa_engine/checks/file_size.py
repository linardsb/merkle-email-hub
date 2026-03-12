"""File size check for email HTML."""

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

_DEFAULT_MAX_SIZE_KB = 102


class FileSizeCheck:
    """Checks that compiled HTML is under the size limit (default: 102KB Gmail clipping)."""

    name = "file_size"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        max_size_kb = (
            config.params.get("max_size_kb", _DEFAULT_MAX_SIZE_KB)
            if config
            else _DEFAULT_MAX_SIZE_KB
        )
        size_kb = len(html.encode("utf-8")) / 1024
        passed = size_kb <= max_size_kb
        score = min(1.0, max_size_kb / max(size_kb, 0.1))
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details=f"Size: {size_kb:.1f}KB (limit: {max_size_kb}KB)",
            severity="error" if not passed else "info",
        )
