"""Repository — all DB operations for Outfit."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item import Item
from app.models.outfit import Outfit
from app.models.outfit_item import OutfitItem
from app.models.outfit_like import OutfitLike
from app.schemas.outfit import OutfitIn, OutfitLikeUserOut, OutfitOut


class OutfitRepository:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def _derive_name(self, item_ids: list[str]) -> str:
        """Build a display name from the item names, e.g. 'White Shirt & Black Jeans'."""
        if not item_ids:
            return "My Outfit"
        uuids = [uuid.UUID(i) for i in item_ids[:3]]
        rows = await self.db.scalars(select(Item).where(Item.id.in_(uuids)))
        items = list(rows.all())
        names = [i.name for i in items if i.name]
        if not names:
            return "My Outfit"
        if len(names) == 1:
            return names[0]
        return " & ".join(names[:2]) + (f" +{len(names)-2}" if len(names) > 2 else "")

    async def create(self, data: OutfitIn) -> OutfitOut:
        name = data.name or await self._derive_name(data.item_ids)
        now = datetime.now(timezone.utc)
        outfit = Outfit(
            user_id=self.user_id,
            name=name,
            occasion=data.occasion,
            vibe=data.vibe,
            mood=data.mood,
            source="manual",
            worn_at=now,
            wear_count=1,
        )
        self.db.add(outfit)
        await self.db.flush()
        await self.db.refresh(outfit)

        for position, item_id_str in enumerate(data.item_ids):
            oi = OutfitItem(
                outfit_id=outfit.id,
                item_id=uuid.UUID(item_id_str),
                position=position,
            )
            self.db.add(oi)

        await self.db.flush()

        return OutfitOut(
            id=outfit.id,
            name=outfit.name,
            occasion=outfit.occasion,
            vibe=outfit.vibe,
            mood=outfit.mood,
            source=outfit.source,
            wear_count=outfit.wear_count,
            worn_at=outfit.worn_at,
            item_ids=data.item_ids,
            likes_count=0,
            liked_by_me=False,
            image_url=outfit.preview_image_url,
            created_at=outfit.created_at,
        )

    def _outfit_select_with_counts(self):
        """Outfit query enriched with likes_count and liked_by_me as columns.

        Avoids materialising every OutfitLike row just to compute len() — the
        likes table can grow without bound per outfit.
        """
        likes_count = (
            select(func.count(OutfitLike.id))
            .where(OutfitLike.outfit_id == Outfit.id)
            .correlate(Outfit)
            .scalar_subquery()
        )
        liked_by_me = exists().where(
            OutfitLike.outfit_id == Outfit.id,
            OutfitLike.user_id == self.user_id,
        )
        return (
            select(
                Outfit,
                likes_count.label("likes_count"),
                liked_by_me.label("liked_by_me"),
            )
            .options(selectinload(Outfit.outfit_items))
        )

    def _to_out(self, outfit: Outfit, likes_count: int, liked_by_me: bool) -> OutfitOut:
        return OutfitOut(
            id=outfit.id,
            name=outfit.name,
            occasion=outfit.occasion,
            vibe=outfit.vibe,
            mood=outfit.mood,
            source=outfit.source,
            wear_count=outfit.wear_count,
            worn_at=outfit.worn_at,
            item_ids=[str(oi.item_id) for oi in outfit.outfit_items],
            likes_count=int(likes_count or 0),
            liked_by_me=bool(liked_by_me),
            image_url=outfit.preview_image_url,
            created_at=outfit.created_at,
        )

    async def get_by_id(self, outfit_id: uuid.UUID) -> OutfitOut | None:
        result = await self.db.execute(
            self._outfit_select_with_counts().where(Outfit.id == outfit_id)
        )
        row = result.first()
        if not row:
            return None
        outfit, likes_count, liked_by_me = row
        return self._to_out(outfit, likes_count, liked_by_me)

    async def get_recent(self, limit: int = 20) -> list[OutfitOut]:
        result = await self.db.execute(
            self._outfit_select_with_counts()
            .where(Outfit.user_id == self.user_id)
            .order_by(Outfit.created_at.desc())
            .limit(limit)
        )
        return [self._to_out(o, lc, lbm) for o, lc, lbm in result.all()]

    async def wear(self, outfit_id: uuid.UUID) -> OutfitOut | None:
        """Mark an existing outfit as worn today, increment wear_count."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(Outfit)
            .where(Outfit.id == outfit_id, Outfit.user_id == self.user_id)
            .values(worn_at=now, wear_count=Outfit.wear_count + 1)
        )
        await self.db.flush()
        return await self.get_by_id(outfit_id)

    async def like(self, outfit_id: uuid.UUID) -> bool:
        """Like an outfit. Returns True if newly liked, False if already liked."""
        existing = await self.db.scalar(
            select(OutfitLike).where(
                OutfitLike.user_id == self.user_id,
                OutfitLike.outfit_id == outfit_id,
            )
        )
        if existing:
            return False

        self.db.add(OutfitLike(user_id=self.user_id, outfit_id=outfit_id))
        await self.db.flush()
        return True

    async def unlike(self, outfit_id: uuid.UUID) -> bool:
        """Unlike an outfit. Returns True if unliked, False if not liked."""
        existing = await self.db.scalar(
            select(OutfitLike).where(
                OutfitLike.user_id == self.user_id,
                OutfitLike.outfit_id == outfit_id,
            )
        )
        if not existing:
            return False

        await self.db.delete(existing)
        await self.db.flush()
        return True

    async def get_taste_vector(self) -> list[float] | None:
        """Mean of the embeddings of outfits the user liked or wore.

        Returns None when the user has no signal yet — caller should fall back
        to e.g. a generic preference embedding.
        """
        # Liked outfits first, then user's own worn outfits as a softer signal.
        liked_rows = await self.db.scalars(
            select(Outfit.embedding)
            .join(OutfitLike, OutfitLike.outfit_id == Outfit.id)
            .where(OutfitLike.user_id == self.user_id, Outfit.embedding.is_not(None))
        )
        vectors = [list(v) for v in liked_rows.all() if v is not None]

        if not vectors:
            worn_rows = await self.db.scalars(
                select(Outfit.embedding)
                .where(
                    Outfit.user_id == self.user_id,
                    Outfit.wear_count > 0,
                    Outfit.embedding.is_not(None),
                )
                .limit(20)
            )
            vectors = [list(v) for v in worn_rows.all() if v is not None]

        if not vectors:
            return None

        dim = len(vectors[0])
        centroid = [0.0] * dim
        for v in vectors:
            for i, x in enumerate(v):
                centroid[i] += x
        n = len(vectors)
        return [x / n for x in centroid]

    async def get_likes(self, outfit_id: uuid.UUID) -> list[OutfitLikeUserOut]:
        likes = await self.db.scalars(
            select(OutfitLike)
            .where(OutfitLike.outfit_id == outfit_id)
            .options(selectinload(OutfitLike.user))
            .order_by(OutfitLike.created_at)
        )
        return [
            OutfitLikeUserOut(
                id=l.user.id,
                display_name=l.user.display_name,
                avatar_url=l.user.avatar_url,
            )
            for l in likes.all()
        ]
