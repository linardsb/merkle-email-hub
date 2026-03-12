"""Image optimization check."""

import re

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult


class ImageOptimizationCheck:
    """Checks image tags for optimization best practices."""

    name = "image_optimization"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        _ = config  # Reserved for future params (e.g., allowed formats)

        issues: list[str] = []
        images = re.findall(r"<img[^>]*>", html, re.IGNORECASE)

        for img in images:
            if "width=" not in img.lower() or "height=" not in img.lower():
                issues.append("Image missing explicit width/height dimensions")
                break
            src_match = re.search(r'src=["\']([^"\']+)["\']', img)
            if src_match and src_match.group(1).lower().endswith(".bmp"):
                issues.append("BMP image format detected — use PNG, JPEG, or WebP")

        total = len(images) if images else 1
        passed = len(issues) == 0
        score = max(0.0, 1.0 - len(issues) / total)
        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(score, 2),
            details="; ".join(issues) if issues else None,
            severity="warning",
        )
