"""File size check for email HTML."""

from app.qa_engine.schemas import QACheckResult

MAX_SIZE_KB = 102


class FileSizeCheck:
    """Checks that compiled HTML is under 102KB (Gmail clipping threshold)."""

    name = "file_size"

    async def run(self, html: str) -> QACheckResult:
        size_kb = len(html.encode("utf-8")) / 1024
        passed = size_kb <= MAX_SIZE_KB
        score = min(1.0, MAX_SIZE_KB / max(size_kb, 0.1))
        return QACheckResult(
            check_name=self.name, passed=passed, score=round(score, 2),
            details=f"Size: {size_kb:.1f}KB (limit: {MAX_SIZE_KB}KB)",
            severity="error" if not passed else "info",
        )
