"""Authentication and JWT settings."""

from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    """Authentication and JWT settings."""

    jwt_secret_key: str = Field(
        default="CHANGE-ME-IN-PRODUCTION-this-is-not-a-real-secret",  # 49 chars; passes min_length, trips prod sentinel
        min_length=32,
        description="HS256 signing key; must be >=32 chars (256 bits). Production refuses the default placeholder.",
    )
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    demo_user_email: str = "demo@example.com"
    demo_user_password: str = "admin"  # noqa: S105
