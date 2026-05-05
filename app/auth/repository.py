"""Database repository for user operations.

Tenant-exempt by design — `User` has no `client_org_id` column; users are
flat global entities with a `role`. Authorization on user-management
endpoints is enforced at the route layer via `Depends(require_role("admin"))`
on every `/users/...` endpoint in `app/auth/routes.py`. The auth `get_service`
factory keeps `Depends(get_db)` (allowlisted pre-auth, see plan §B), so
`scoped_access` would `RuntimeError` on every login / refresh / bootstrap
call. See `.agents/plans/tech-debt-03-multi-tenant-isolation.md` §A1.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.shared.models import utcnow
from app.shared.utils import escape_like


class UserRepository:
    """Handles all database operations for User model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_email(self, email: str) -> User | None:
        """Find a user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: int) -> User | None:
        """Find a user by database ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Create a new user."""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Update an existing user (e.g., failed_attempts, locked_until)."""
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """Soft delete a user by setting deleted_at timestamp."""
        user.deleted_at = utcnow()
        user.is_active = False
        await self.db.flush()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        """List users with pagination and filtering."""
        query = select(User).where(User.deleted_at.is_(None))
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(
                or_(
                    User.name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )
        if role is not None:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active.is_(is_active))
        query = query.order_by(User.name).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        *,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Count users matching the given filters."""
        query = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(
                or_(
                    User.name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )
        if role is not None:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active.is_(is_active))
        result = await self.db.execute(query)
        return result.scalar_one()

    async def count(self) -> int:
        """Count total users."""
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        )
        return result.scalar_one()
