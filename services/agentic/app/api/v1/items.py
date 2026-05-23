"""Clothing items — route handlers only."""
from __future__ import annotations

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.repositories.clothing import ClothingItemRepository
from app.schemas.clothing import ClothingItemIn, ClothingItemOut
from app.services.jwt import get_current_user_id_verified as get_current_user_id

router = APIRouter(prefix="/wardrobe/items", tags=["clothing-items"])


def _user_id(current_user_id: Annotated[str, Depends(get_current_user_id)]) -> uuid.UUID:
    return uuid.UUID(current_user_id)


@router.get("", response_model=List[ClothingItemOut])
async def list_items(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(_user_id),
):
    repo = ClothingItemRepository(db, user_id)
    items = await repo.get_all()
    return [ClothingItemOut.from_item(i) for i in items]


@router.post("", response_model=ClothingItemOut, status_code=201)
async def create_item(
    body: ClothingItemIn,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(_user_id),
):
    repo = ClothingItemRepository(db, user_id)
    item = await repo.create(body)
    return ClothingItemOut.from_item(item)


@router.post("/demo-seed", response_model=List[ClothingItemOut], status_code=201)
async def seed_demo_items(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(_user_id),
):
    repo = ClothingItemRepository(db, user_id)
    if await repo.has_any():
        raise HTTPException(status_code=409, detail="User already has wardrobe items")
    items = await repo.seed_demo()
    return [ClothingItemOut.from_item(i) for i in items]


@router.get("/{item_id}/similar", response_model=List[ClothingItemOut])
async def similar_items(
    item_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    same_category_only: bool = Query(
        False,
        description="If true, only return items in the same category as the anchor.",
    ),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(_user_id),
):
    """Nearest neighbours of an item from the user's wardrobe by embedding cosine
    distance. Returns an empty list if the anchor has no embedding."""
    repo = ClothingItemRepository(db, user_id)
    anchor = await repo.get_by_id(item_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail="Item not found")
    neighbours = await repo.find_similar(item_id, limit=limit, same_category_only=same_category_only)
    return [ClothingItemOut.from_item(i) for i in neighbours]
