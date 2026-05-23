"""Gallery endpoints — curated public/private outfit collections."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database import get_db
from app.models.gallery import Gallery, GalleryOutfit
from app.models.outfit import Outfit
from app.schemas.gallery import (
    GalleryCreate,
    GalleryDetailOut,
    GalleryOut,
    GalleryOutfitAdd,
    GalleryUpdate,
    OutfitSummary,
)
from app.services.jwt import get_current_user_id_verified

router = APIRouter(prefix="/galleries", tags=["galleries"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_owned_gallery_or_404(db: AsyncSession, gallery_id: uuid.UUID, user_id: uuid.UUID) -> Gallery:
    gallery = await db.get(Gallery, gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Gallery not found")
    if gallery.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your gallery")
    return gallery


def _to_gallery_out(gallery: Gallery, outfit_count: int) -> GalleryOut:
    return GalleryOut(
        id=gallery.id,
        user_id=gallery.user_id,
        name=gallery.name,
        description=gallery.description,
        cover_image_url=gallery.cover_image_url,
        is_public=gallery.is_public,
        outfit_count=outfit_count,
        created_at=gallery.created_at,
        updated_at=gallery.updated_at,
    )


# ── Gallery CRUD ──────────────────────────────────────────────────────────────

@router.post("", response_model=GalleryOut, status_code=201)
async def create_gallery(
    body: GalleryCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> GalleryOut:
    gallery = Gallery(
        user_id=uuid.UUID(current_user_id),
        name=body.name,
        description=body.description,
        cover_image_url=body.cover_image_url,
        is_public=body.is_public,
    )
    db.add(gallery)
    await db.flush()
    await db.refresh(gallery)
    return _to_gallery_out(gallery, 0)


@router.get("", response_model=List[GalleryOut])
async def list_my_galleries(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> List[GalleryOut]:
    user_id = uuid.UUID(current_user_id)
    result = await db.execute(
        select(Gallery, func.count(GalleryOutfit.id).label("outfit_count"))
        .outerjoin(GalleryOutfit, GalleryOutfit.gallery_id == Gallery.id)
        .where(Gallery.user_id == user_id)
        .group_by(Gallery.id)
        .order_by(Gallery.created_at.desc())
    )
    return [_to_gallery_out(g, count) for g, count in result.all()]


@router.get("/public", response_model=List[GalleryOut])
async def list_public_galleries(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> List[GalleryOut]:
    result = await db.execute(
        select(Gallery, func.count(GalleryOutfit.id).label("outfit_count"))
        .outerjoin(GalleryOutfit, GalleryOutfit.gallery_id == Gallery.id)
        .where(Gallery.is_public.is_(True))
        .group_by(Gallery.id)
        .order_by(Gallery.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_to_gallery_out(g, count) for g, count in result.all()]


@router.get("/{gallery_id}", response_model=GalleryDetailOut)
async def get_gallery(
    gallery_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> GalleryDetailOut:
    user_id = uuid.UUID(current_user_id)
    result = await db.execute(
        select(Gallery)
        .options(selectinload(Gallery.gallery_outfits).selectinload(GalleryOutfit.outfit))
        .where(Gallery.id == gallery_id)
    )
    gallery = result.scalar_one_or_none()
    if not gallery:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Only owner can see private galleries
    if not gallery.is_public and gallery.user_id != user_id:
        raise HTTPException(status_code=403, detail="This gallery is private")

    outfits = [OutfitSummary.model_validate(go.outfit) for go in gallery.gallery_outfits]
    count = len(outfits)

    return GalleryDetailOut(
        id=gallery.id,
        user_id=gallery.user_id,
        name=gallery.name,
        description=gallery.description,
        cover_image_url=gallery.cover_image_url or (outfits[0].preview_image_url if outfits else None),
        is_public=gallery.is_public,
        outfit_count=count,
        created_at=gallery.created_at,
        updated_at=gallery.updated_at,
        outfits=outfits,
    )


@router.patch("/{gallery_id}", response_model=GalleryOut)
async def update_gallery(
    gallery_id: uuid.UUID,
    body: GalleryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> GalleryOut:
    user_id = uuid.UUID(current_user_id)
    gallery = await _get_owned_gallery_or_404(db, gallery_id, user_id)

    if body.name is not None:
        gallery.name = body.name
    if body.description is not None:
        gallery.description = body.description
    if body.cover_image_url is not None:
        gallery.cover_image_url = body.cover_image_url
    if body.is_public is not None:
        gallery.is_public = body.is_public

    await db.flush()
    await db.refresh(gallery)

    count_result = await db.scalar(
        select(func.count(GalleryOutfit.id)).where(GalleryOutfit.gallery_id == gallery_id)
    )
    return _to_gallery_out(gallery, count_result or 0)


@router.delete("/{gallery_id}", status_code=204)
async def delete_gallery(
    gallery_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> None:
    user_id = uuid.UUID(current_user_id)
    gallery = await _get_owned_gallery_or_404(db, gallery_id, user_id)
    await db.delete(gallery)
    await db.flush()


# ── Outfit membership ─────────────────────────────────────────────────────────

@router.post("/{gallery_id}/outfits", status_code=201)
async def add_outfit_to_gallery(
    gallery_id: uuid.UUID,
    body: GalleryOutfitAdd,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> dict:
    user_id = uuid.UUID(current_user_id)
    await _get_owned_gallery_or_404(db, gallery_id, user_id)

    outfit = await db.get(Outfit, body.outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    if outfit.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your outfit")

    existing = await db.scalar(
        select(GalleryOutfit).where(
            GalleryOutfit.gallery_id == gallery_id,
            GalleryOutfit.outfit_id == body.outfit_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Outfit already in this gallery")

    max_pos = await db.scalar(
        select(func.coalesce(func.max(GalleryOutfit.position), -1)).where(
            GalleryOutfit.gallery_id == gallery_id
        )
    )

    entry = GalleryOutfit(
        gallery_id=gallery_id,
        outfit_id=body.outfit_id,
        position=(max_pos or 0) + 1,
    )
    db.add(entry)
    await db.flush()

    return {"gallery_id": str(gallery_id), "outfit_id": str(body.outfit_id), "position": entry.position}


@router.delete("/{gallery_id}/outfits/{outfit_id}", status_code=204)
async def remove_outfit_from_gallery(
    gallery_id: uuid.UUID,
    outfit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> None:
    user_id = uuid.UUID(current_user_id)
    await _get_owned_gallery_or_404(db, gallery_id, user_id)

    entry = await db.scalar(
        select(GalleryOutfit).where(
            GalleryOutfit.gallery_id == gallery_id,
            GalleryOutfit.outfit_id == outfit_id,
        )
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Outfit not in this gallery")

    await db.delete(entry)
    await db.flush()
