"""Business logic for item management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.example.exceptions import ItemAlreadyExistsError, ItemNotFoundError
from app.example.repository import ItemRepository
from app.example.schemas import (
    ItemCreate,
    ItemResponse,
    ItemUpdate,
)
from app.shared.schemas import PaginatedResponse, PaginationParams

logger = get_logger(__name__)


class ItemService:
    """Business logic for item management."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            db: SQLAlchemy async session.
        """
        self.db = db
        self.repository = ItemRepository(db)

    async def get_item(self, item_id: int) -> ItemResponse:
        """Get an item by ID.

        Args:
            item_id: The item's database ID.

        Returns:
            ItemResponse for the found item.

        Raises:
            ItemNotFoundError: If item does not exist.
        """
        logger.info("items.fetch_started", item_id=item_id)

        item = await self.repository.get(item_id)
        if not item:
            logger.warning("items.fetch_failed", item_id=item_id, reason="not_found")
            raise ItemNotFoundError(f"Item {item_id} not found")

        logger.info("items.fetch_completed", item_id=item_id)
        return ItemResponse.model_validate(item)

    async def list_items(
        self,
        pagination: PaginationParams,
        *,
        search: str | None = None,
        active_only: bool = True,
        status: str | None = None,
    ) -> PaginatedResponse[ItemResponse]:
        """List items with pagination and optional filtering.

        Args:
            pagination: Page and page_size parameters.
            search: Case-insensitive search on name.
            active_only: If True, only return active items.
            status: Filter by item status.

        Returns:
            Paginated list of ItemResponse items.
        """
        logger.info(
            "items.list_started",
            page=pagination.page,
            page_size=pagination.page_size,
            search=search,
            status=status,
        )

        items = await self.repository.list(
            offset=pagination.offset,
            limit=pagination.page_size,
            active_only=active_only,
            search=search,
            status=status,
        )
        total = await self.repository.count(
            active_only=active_only,
            search=search,
            status=status,
        )

        response_items = [ItemResponse.model_validate(i) for i in items]

        logger.info("items.list_completed", result_count=len(response_items), total=total)

        return PaginatedResponse[ItemResponse](
            items=response_items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def create_item(self, data: ItemCreate) -> ItemResponse:
        """Create a new item.

        Args:
            data: Item creation data.

        Returns:
            ItemResponse for the created item.

        Raises:
            ItemAlreadyExistsError: If name already exists.
        """
        logger.info("items.create_started", name=data.name)

        existing = await self.repository.get_by_name(data.name)
        if existing:
            logger.warning(
                "items.create_failed",
                name=data.name,
                reason="duplicate",
            )
            raise ItemAlreadyExistsError(
                f"Item with name '{data.name}' already exists"
            )

        item = await self.repository.create(data)
        logger.info(
            "items.create_completed",
            item_id=item.id,
            name=item.name,
        )

        return ItemResponse.model_validate(item)

    async def update_item(self, item_id: int, data: ItemUpdate) -> ItemResponse:
        """Update an existing item.

        Args:
            item_id: The item's database ID.
            data: Fields to update.

        Returns:
            ItemResponse for the updated item.

        Raises:
            ItemNotFoundError: If item does not exist.
            ItemAlreadyExistsError: If updating name to a duplicate.
        """
        logger.info("items.update_started", item_id=item_id)

        item = await self.repository.get(item_id)
        if not item:
            logger.warning("items.update_failed", item_id=item_id, reason="not_found")
            raise ItemNotFoundError(f"Item {item_id} not found")

        # Check for duplicate name if it's being changed
        update_fields = data.model_dump(exclude_unset=True)
        new_name = update_fields.get("name")
        if isinstance(new_name, str) and new_name != item.name:
            existing = await self.repository.get_by_name(new_name)
            if existing:
                logger.warning(
                    "items.update_failed",
                    item_id=item_id,
                    name=new_name,
                    reason="duplicate",
                )
                raise ItemAlreadyExistsError(
                    f"Item with name '{new_name}' already exists"
                )

        item = await self.repository.update(item, data)
        logger.info("items.update_completed", item_id=item.id)

        return ItemResponse.model_validate(item)

    async def delete_item(self, item_id: int) -> None:
        """Delete an item by ID.

        Args:
            item_id: The item's database ID.

        Raises:
            ItemNotFoundError: If item does not exist.
        """
        logger.info("items.delete_started", item_id=item_id)

        item = await self.repository.get(item_id)
        if not item:
            logger.warning("items.delete_failed", item_id=item_id, reason="not_found")
            raise ItemNotFoundError(f"Item {item_id} not found")

        await self.repository.delete(item)
        logger.info("items.delete_completed", item_id=item_id)
