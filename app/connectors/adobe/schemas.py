"""Adobe Campaign-specific schemas."""

from pydantic import BaseModel, Field


class AdobeDeliveryFragment(BaseModel):
    """Schema representing an Adobe Campaign delivery content fragment."""

    name: str = Field(..., min_length=1, max_length=200)
    content_type: str = "html"
    content: str = Field(..., min_length=1)
    folder_id: str | None = None
    label: str | None = None
