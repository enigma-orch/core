"""Repository — all DB operations for wardrobe items (backed by the Item model)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.schemas.clothing import ClothingItemIn


class ClothingItemRepository:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def get_all(self) -> list[Item]:
        rows = await self.db.scalars(
            select(Item)
            .where(Item.user_id == self.user_id)
            .order_by(Item.created_at.desc())
        )
        return list(rows.all())

    async def create(self, data: ClothingItemIn) -> Item:
        item = Item(
            user_id=self.user_id,
            name=data.name,
            category=data.category,
            colors=data.colors,
            brand=data.brand,
            style_tags=data.style_tags,
            original_image_url=data.image_url,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get_by_id(self, item_id: uuid.UUID) -> Item | None:
        return await self.db.scalar(
            select(Item).where(Item.id == item_id, Item.user_id == self.user_id)
        )

    async def find_similar(
        self,
        item_id: uuid.UUID,
        limit: int = 10,
        same_category_only: bool = False,
    ) -> list[Item]:
        """Cosine-distance neighbours of `item_id` within the user's wardrobe.

        Excludes the source item and any items without an embedding.
        """
        anchor = await self.get_by_id(item_id)
        if anchor is None or anchor.embedding is None:
            return []

        stmt = (
            select(Item)
            .where(
                Item.user_id == self.user_id,
                Item.id != item_id,
                Item.embedding.is_not(None),
            )
            .order_by(Item.embedding.cosine_distance(anchor.embedding))
            .limit(limit)
        )
        if same_category_only and anchor.category:
            stmt = stmt.where(Item.category == anchor.category)
        rows = await self.db.scalars(stmt)
        return list(rows.all())

    async def find_candidates_by_vector(
        self,
        vector: list[float],
        category: str | None = None,
        limit: int = 10,
    ) -> list[Item]:
        """Generic ANN lookup against the user's wardrobe by an arbitrary vector."""
        stmt = (
            select(Item)
            .where(Item.user_id == self.user_id, Item.embedding.is_not(None))
            .order_by(Item.embedding.cosine_distance(vector))
            .limit(limit)
        )
        if category:
            stmt = stmt.where(Item.category == category)
        rows = await self.db.scalars(stmt)
        return list(rows.all())

    async def has_any(self) -> bool:
        result = await self.db.scalar(
            select(Item).where(Item.user_id == self.user_id).limit(1)
        )
        return result is not None

    async def seed_demo(self) -> list[Item]:
        demos = [
            Item(user_id=self.user_id, name="White Oxford Shirt", category="top",       colors=["white"], brand="COS",         style_tags=["smart-casual", "minimal"],
                 original_image_url="https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=600&q=80"),
            Item(user_id=self.user_id, name="Black Slim Jeans",   category="bottom",    colors=["black"], brand="Levi's",      style_tags=["casual", "everyday"],
                 original_image_url="https://images.unsplash.com/photo-1604176354204-9268737828e4?w=600&q=80"),
            Item(user_id=self.user_id, name="Cream Hoodie",       category="top",       colors=["cream"], brand="Nike",        style_tags=["casual", "streetwear"],
                 original_image_url="https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=600&q=80"),
            Item(user_id=self.user_id, name="White Sneakers",     category="shoes",     colors=["white"], brand="New Balance", style_tags=["casual", "sport"],
                 original_image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80"),
            Item(user_id=self.user_id, name="Camel Overcoat",     category="outerwear", colors=["camel"], brand="Zara",        style_tags=["smart-casual", "winter"],
                 original_image_url="https://images.unsplash.com/photo-1544022613-e87ca75a784a?w=600&q=80"),
            Item(user_id=self.user_id, name="Navy Chinos",        category="bottom",    colors=["navy"],  brand="Uniqlo",      style_tags=["smart-casual"],
                 original_image_url="https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=600&q=80"),
        ]
        self.db.add_all(demos)
        await self.db.flush()
        for item in demos:
            await self.db.refresh(item)
        return demos
