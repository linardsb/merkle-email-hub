"""Request/response schemas for the Outlook Fixer agent."""

from pydantic import BaseModel, Field

from app.qa_engine.schemas import QACheckResult


class OutlookFixerRequest(BaseModel):
    """Request body for the Outlook Fixer process endpoint.

    Attributes:
        html: Existing email HTML with Outlook rendering issues.
        issues: Optional list of specific issues to fix (e.g., 'vml', 'ghost_tables').
            When None, the agent auto-detects all Outlook issues.
        stream: Whether to return SSE streaming response.
        run_qa: Whether to run the 10-point QA gate on the fixed HTML.
    """

    html: str = Field(min_length=50, max_length=200_000, description="Email HTML to fix")
    issues: list[str] | None = Field(
        default=None,
        description="Specific Outlook issues to fix (auto-detect if None)",
    )
    stream: bool = False
    run_qa: bool = False


class OutlookFixerResponse(BaseModel):
    """Response from the Outlook Fixer process endpoint.

    Attributes:
        html: The fixed email HTML with Outlook issues resolved.
        fixes_applied: List of fixes that were applied.
        qa_results: Individual QA check results (only when run_qa=True).
        qa_passed: Overall QA pass/fail (only when run_qa=True).
        model: The model identifier that processed the HTML.
    """

    html: str
    fixes_applied: list[str] = Field(default_factory=list)
    qa_results: list[QACheckResult] | None = None
    qa_passed: bool | None = None
    model: str
