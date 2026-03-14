"""Stage 1: HTML structure repair — ensure DOCTYPE, html, head, body exist."""

from __future__ import annotations

import re

from app.qa_engine.repair.pipeline import RepairResult


class StructureRepair:
    """Ensure minimal valid HTML skeleton."""

    @property
    def name(self) -> str:
        return "structure"

    def repair(self, html: str) -> RepairResult:
        repairs: list[str] = []
        result = html

        # Add DOCTYPE if missing
        if not re.match(r"\s*<!DOCTYPE", result, re.IGNORECASE):
            result = "<!DOCTYPE html>\n" + result
            repairs.append("added_doctype")

        # Add <html> wrapper if missing
        if not re.search(r"<html[\s>]", result, re.IGNORECASE):
            result = result.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n<html>\n", 1)
            result += "\n</html>"
            repairs.append("added_html")

        # Add <head> if missing (insert after <html...>)
        if not re.search(r"<head[\s>]", result, re.IGNORECASE):
            html_tag_match = re.search(r"<html[^>]*>", result, re.IGNORECASE)
            if html_tag_match:
                insert_pos = html_tag_match.end()
                result = result[:insert_pos] + "\n<head></head>" + result[insert_pos:]
                repairs.append("added_head")

        # Add <body> if missing (insert after </head>)
        if not re.search(r"<body[\s>]", result, re.IGNORECASE):
            head_close = re.search(r"</head\s*>", result, re.IGNORECASE)
            if head_close:
                insert_pos = head_close.end()
                remaining = result[insert_pos:]
                # Don't wrap </html> in body
                html_close_match = re.search(r"</html\s*>", remaining, re.IGNORECASE)
                if html_close_match:
                    body_content = remaining[: html_close_match.start()]
                    after_html = remaining[html_close_match.start() :]
                    result = (
                        result[:insert_pos] + "\n<body>" + body_content + "</body>\n" + after_html
                    )
                else:
                    result = result[:insert_pos] + "\n<body>" + remaining + "</body>"
                repairs.append("added_body")

        return RepairResult(html=result, repairs_applied=repairs)
