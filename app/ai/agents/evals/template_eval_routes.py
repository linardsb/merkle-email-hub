# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API for managing template-sourced eval cases."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.requests import Request

from app.ai.agents.evals.template_eval_generator import TemplateEvalGenerator
from app.ai.agents.evals.template_eval_schemas import (
    TemplateEvalCase,
    TemplateEvalCaseSet,
    TemplateEvalSummary,
    TemplateEvalTemplateSummary,
)
from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.exceptions import NotFoundError
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/v1/evals/templates", tags=["eval-templates"])


@router.get("", response_model=TemplateEvalSummary)
@limiter.limit("30/minute")
async def list_template_eval_cases(
    request: Request,  # noqa: ARG001
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> TemplateEvalSummary:
    """List all template-sourced eval cases with summary."""
    gen = TemplateEvalGenerator()
    all_cases = gen.load_all()

    templates: list[TemplateEvalTemplateSummary] = []
    total_cases = 0
    for name, cases in all_cases.items():
        total_cases += len(cases)
        case_types = sorted({str(c.get("case_type", "unknown")) for c in cases})
        generated_at = str(cases[0].get("created_at", "")) if cases else ""
        templates.append(
            TemplateEvalTemplateSummary(
                template_name=name,
                case_count=len(cases),
                case_types=case_types,
                generated_at=generated_at,
            )
        )

    return TemplateEvalSummary(
        total_templates=len(all_cases),
        total_cases=total_cases,
        templates=templates,
    )


@router.get("/{template_name}/cases", response_model=TemplateEvalCaseSet)
@limiter.limit("30/minute")
async def get_template_eval_cases(
    request: Request,  # noqa: ARG001
    template_name: str,
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> TemplateEvalCaseSet:
    """Get eval cases for a specific uploaded template."""
    gen = TemplateEvalGenerator()
    data = gen.load_case_set(template_name)
    if data is None:
        raise NotFoundError(f"No eval cases found for template '{template_name}'")

    return TemplateEvalCaseSet(
        template_name=template_name,
        cases=[TemplateEvalCase.model_validate(c) for c in data["cases"]],
        generated_at=str(data.get("generated_at", "")),
    )


@router.delete("/{template_name}/cases", status_code=204)
@limiter.limit("10/minute")
async def delete_template_eval_cases(
    request: Request,  # noqa: ARG001
    template_name: str,
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> None:
    """Delete eval cases for a template (e.g., when template is deleted)."""
    gen = TemplateEvalGenerator()
    gen.delete(template_name)
