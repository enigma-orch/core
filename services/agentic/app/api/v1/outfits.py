"""Outfits — route handlers only."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.repositories.outfit import OutfitRepository
from app.schemas.outfit import OutfitIn, OutfitLikeUserOut, OutfitOut
from app.services.jwt import get_current_user_id_verified as get_current_user_id

router = APIRouter(prefix="/outfits", tags=["outfits"])


@router.post("", response_model=OutfitOut, status_code=201)
async def create_outfit(
    body: OutfitIn,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = OutfitRepository(db, uuid.UUID(user_id))
    return await repo.create(body)


@router.get("", response_model=List[OutfitOut])
async def list_outfits(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = OutfitRepository(db, uuid.UUID(user_id))
    return await repo.get_recent()


@router.get("/{outfit_id}", response_model=OutfitOut)
async def get_outfit(
    outfit_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = OutfitRepository(db, uuid.UUID(user_id))
    outfit = await repo.get_by_id(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return outfit


@router.post("/{outfit_id}/wear", response_model=OutfitOut, status_code=200)
async def wear_outfit(
    outfit_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = OutfitRepository(db, uuid.UUID(user_id))
    outfit = await repo.wear(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return outfit


@router.post("/{outfit_id}/like", status_code=200)
async def like_outfit(
    outfit_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = OutfitRepository(db, uuid.UUID(user_id))
    outfit = await repo.get_by_id(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    liked = await repo.like(outfit_id)
    return {"liked": liked, "likes_count": outfit.likes_count + (1 if liked else 0)}


@router.delete("/{outfit_id}/like", status_code=200)
async def unlike_outfit(
    outfit_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = OutfitRepository(db, uuid.UUID(user_id))
    outfit = await repo.get_by_id(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    unliked = await repo.unlike(outfit_id)
    return {"unliked": unliked, "likes_count": max(0, outfit.likes_count - (1 if unliked else 0))}


@router.get("/{outfit_id}/likes", response_model=List[OutfitLikeUserOut])
async def get_outfit_likes(
    outfit_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = OutfitRepository(db, uuid.UUID(user_id))
    outfit = await repo.get_by_id(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return await repo.get_likes(outfit_id)
