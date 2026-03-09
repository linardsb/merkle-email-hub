"""Request/response schemas for the Code Reviewer agent."""

from typing import Literal

from pydantic import BaseModel, Field

from app.qa_engine.schemas import QACheckResult

ReviewFocus = Literal[
    "redundant_code",
    "css_support",
    "nesting",
    "file_size",
    "all",
]

IssueSeverity = Literal["critical", "warning", "info"]


class CodeReviewIssue(BaseModel):
    """A single code review finding."""

    rule: str = Field(
        description="Rule identifier (e.g., 'redundant-mso-comment', 'unsupported-css-grid')"
    )
    severity: IssueSeverity
    line_hint: int | None = Field(default=None, description="Approximate line number (best effort)")
    message: str = Field(description="Human-readable description of the issue")
    suggestion: str | None = Field(default=None, description="Actionable fix suggestion")


class CodeReviewRequest(BaseModel):
    """Request body for the Code Reviewer process endpoint."""

    html: str = Field(min_length=50, max_length=200_000, description="Email HTML to review")
    focus: ReviewFocus = Field(default="all", description="Area to focus the review on")
    stream: bool = False
    run_qa: bool = False


class CodeReviewResponse(BaseModel):
    """Response from the Code Reviewer process endpoint."""

    html: str = Field(description="Original HTML (unmodified)")
    issues: list[CodeReviewIssue] = Field(default_factory=list)
    summary: str = Field(description="Brief natural-language review summary")
    skills_loaded: list[str] = Field(default_factory=list)
    qa_results: list[QACheckResult] | None = None
    qa_passed: bool | None = None
    model: str
