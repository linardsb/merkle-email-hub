"""Shared Pydantic schemas for common patterns."""

import math
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters for list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate the offset for database queries."""
        return (self.page - 1) * self.page_size


class PaginatedResponse[T](BaseModel):
    """Standard paginated response format."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 0
        return math.ceil(self.total / self.page_size)


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str
    type: str
    detail: str | None = None
