from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GalleryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    cover_image_url: Optional[str] = None
    is_public: bool = False


class GalleryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    cover_image_url: Optional[str] = None
    is_public: Optional[bool] = None


class GalleryOutfitAdd(BaseModel):
    outfit_id: uuid.UUID


# ── Nested outfit summary inside gallery response ─────────────────────────────

class OutfitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: Optional[str] = None
    preview_image_url: Optional[str] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    source: str
    created_at: datetime


class GalleryOutfitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gallery_id: uuid.UUID
    outfit_id: uuid.UUID
    position: int
    added_at: datetime = Field(alias=None)
    outfit: OutfitSummary

    @classmethod
    def from_orm_entry(cls, entry: object) -> "GalleryOutfitOut":
        return cls(
            id=entry.id,
            gallery_id=entry.gallery_id,
            outfit_id=entry.outfit_id,
            position=entry.position,
            added_at=entry.created_at,
            outfit=OutfitSummary.model_validate(entry.outfit),
        )


class GalleryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_public: bool
    outfit_count: int = 0
    created_at: datetime
    updated_at: datetime


class GalleryDetailOut(GalleryOut):
    outfits: List[OutfitSummary] = []
