"""POST /api/v1/wardrobe/outfits/complete — fill missing slots around anchor items."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.repositories.clothing import ClothingItemRepository
from app.schemas.wardrobe import ItemOut
from app.services.jwt import get_current_user_id_verified

router = APIRouter(prefix="/wardrobe/outfits", tags=["outfit-complete"])

# Which slots to fill, and which anchor categories already cover them.
_TARGET_SLOTS = ["top", "bottom", "shoes", "outerwear"]
_DRESS_COVERS = {"top", "bottom"}


class OutfitCompleteRequest(BaseModel):
    item_ids: List[uuid.UUID] = Field(..., min_length=1, max_length=3)
    per_slot: int = Field(3, ge=1, le=5)


class SlotSuggestion(BaseModel):
    category: str
    items: List[ItemOut]


class OutfitCompleteResponse(BaseModel):
    anchors: List[ItemOut]
    slots: List[SlotSuggestion]


def _slots_to_fill(anchor_categories: set[str]) -> list[str]:
    covered = set(anchor_categories)
    if "dress" in covered:
        covered |= _DRESS_COVERS
    return [s for s in _TARGET_SLOTS if s not in covered]


def _mean_vector(vectors: list[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i, x in enumerate(v):
            out[i] += x
    return [x / len(vectors) for x in out]


@router.post("/complete", response_model=OutfitCompleteResponse)
async def complete_outfit(
    body: OutfitCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> OutfitCompleteResponse:
    user_id = uuid.UUID(current_user_id)
    repo = ClothingItemRepository(db, user_id)

    anchors = []
    for iid in body.item_ids:
        item = await repo.get_by_id(iid)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {iid} not found")
        anchors.append(item)

    anchor_ids = {a.id for a in anchors}
    anchor_categories = {(a.category or "").lower() for a in anchors}
    slots_needed = _slots_to_fill(anchor_categories)
    if not slots_needed:
        return OutfitCompleteResponse(
            anchors=[ItemOut.model_validate(a) for a in anchors],
            slots=[],
        )

    anchor_vectors = [list(a.embedding) for a in anchors if a.embedding is not None]
    centroid = _mean_vector(anchor_vectors)
    if centroid is None:
        raise HTTPException(
            status_code=400,
            detail="Anchor items have no embeddings yet — re-upload to enrich them.",
        )

    slot_suggestions: list[SlotSuggestion] = []
    for category in slots_needed:
        candidates = await repo.find_candidates_by_vector(
            centroid, category=category, limit=body.per_slot + len(anchor_ids)
        )
        filtered = [c for c in candidates if c.id not in anchor_ids][: body.per_slot]
        if filtered:
            slot_suggestions.append(
                SlotSuggestion(
                    category=category,
                    items=[ItemOut.model_validate(c) for c in filtered],
                )
            )

    return OutfitCompleteResponse(
        anchors=[ItemOut.model_validate(a) for a in anchors],
        slots=slot_suggestions,
    )
