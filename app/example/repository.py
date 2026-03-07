"""Data access layer for item management."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.example.models import Item
from app.example.schemas import ItemCreate, ItemUpdate
from app.shared.models import utcnow
from app.shared.utils import escape_like


class ItemRepository:
    """Database operations for items."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            db: SQLAlchemy async session.
        """
        self.db = db

    async def get(self, item_id: int) -> Item | None:
        """Get an item by primary key ID.

        Args:
            item_id: The item's database ID.

        Returns:
            Item instance or None if not found.
        """
        result = await self.db.execute(
            select(Item).where(Item.id == item_id, Item.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Item | None:
        """Get an item by name.

        Args:
            name: The item name.

        Returns:
            Item instance or None if not found.
        """
        result = await self.db.execute(
            select(Item).where(Item.name == name, Item.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        active_only: bool = True,
        search: str | None = None,
        status: str | None = None,
    ) -> list[Item]:
        """List items with pagination and filtering.

        Args:
            offset: Number of records to skip.
            limit: Maximum records to return.
            active_only: If True, only return active items.
            search: Case-insensitive search on name.
            status: Filter by item status.

        Returns:
            List of Item instances.
        """
        query = select(Item).where(Item.deleted_at.is_(None))
        if active_only:
            query = query.where(Item.is_active.is_(True))
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Item.name.ilike(pattern))
        if status is not None:
            query = query.where(Item.status == status)
        query = query.order_by(Item.name).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        active_only: bool = True,
        search: str | None = None,
        status: str | None = None,
    ) -> int:
        """Count items matching the given filters.

        Args:
            active_only: If True, only count active items.
            search: Case-insensitive search on name.
            status: Filter by item status.

        Returns:
            Total number of matching items.
        """
        query = select(func.count()).select_from(Item).where(Item.deleted_at.is_(None))
        if active_only:
            query = query.where(Item.is_active.is_(True))
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Item.name.ilike(pattern))
        if status is not None:
            query = query.where(Item.status == status)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, data: ItemCreate) -> Item:
        """Create a new item record.

        Args:
            data: Item creation data.

        Returns:
            The newly created Item instance.
        """
        item = Item(**data.model_dump())
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update(self, item: Item, data: ItemUpdate) -> Item:
        """Update an existing item record.

        Args:
            item: The item instance to update.
            data: Fields to update (only set fields are applied).

        Returns:
            The updated Item instance.
        """
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, item: Item) -> None:
        """Soft delete an item by setting deleted_at timestamp.

        Args:
            item: The item instance to delete.
        """
        item.deleted_at = utcnow()
        await self.db.commit()
