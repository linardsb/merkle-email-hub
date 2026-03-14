"""Request/response schemas for the Scaffolder agent."""

from typing import Literal

from pydantic import BaseModel, Field

from app.qa_engine.schemas import QACheckResult


class ScaffolderRequest(BaseModel):
    """Request body for the scaffolder generate endpoint.

    Attributes:
        brief: The campaign brief describing the email to generate.
        stream: Whether to return SSE streaming response.
        run_qa: Whether to run the 10-point QA gate on the generated HTML.
        output_mode: "html" for raw LLM HTML, "structured" for template-first pipeline.
    """

    brief: str = Field(min_length=10, max_length=4000, description="Campaign brief")
    stream: bool = False
    run_qa: bool = False
    output_mode: Literal["html", "structured"] = "html"
    brand_config: dict[str, object] | None = Field(
        default=None,
        description="Brand guidelines for design token selection (colours, fonts, etc.)",
    )


class ScaffolderResponse(BaseModel):
    """Response from the scaffolder generate endpoint.

    Attributes:
        html: The generated Maizzle email HTML.
        qa_results: Individual QA check results (only when run_qa=True).
        qa_passed: Overall QA pass/fail (only when run_qa=True).
        model: The model identifier that generated the HTML.
        plan: Structured build plan (only when output_mode="structured").
    """

    html: str
    qa_results: list[QACheckResult] | None = None
    qa_passed: bool | None = None
    model: str
    confidence: float | None = None
    skills_loaded: list[str] = Field(default_factory=list)
    mso_warnings: list[str] = Field(default_factory=list)
    plan: dict[str, object] | None = None
