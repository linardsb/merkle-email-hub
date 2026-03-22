"""Pydantic schemas for the export approval gate."""

from __future__ import annotations

import datetime

from pydantic import BaseModel


class ApprovalGateResult(BaseModel):
    """Result of the export approval gate evaluation."""

    required: bool
    passed: bool
    reason: str | None = None
    approval_id: int | None = None
    approved_by: str | None = None
    approved_at: datetime.datetime | None = None
