"""Pydantic schemas for clothing item requests and responses."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.item import Item


class ClothingItemIn(BaseModel):
    name: str
    category: str
    colors: List[str] = []
    brand: Optional[str] = None
    style_tags: List[str] = []
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClothingItemOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID

    # Image — clean only, no original
    image_url: Optional[str] = None

    # Core metadata
    name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None

    # Style attributes
    colors: List[str] = []
    season: List[str] = []
    occasion: Optional[str] = None
    style_tags: List[str] = []
    pattern: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None

    # Physical
    size: Optional[str] = None
    notes: Optional[str] = None

    # Wear tracking
    wear_count: int = 0
    last_worn_at: Optional[datetime] = None

    # Enrichment
    enriched: bool = False
    enrichment_data: Optional[dict] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_item(cls, item: Item) -> "ClothingItemOut":
        return cls(
            id=item.id,
            user_id=item.user_id,
            image_url=item.clean_image_url or item.original_image_url,
            name=item.name,
            category=item.category,
            subcategory=item.subcategory,
            brand=item.brand,
            colors=item.colors or [],
            season=item.season or [],
            occasion=item.occasion,
            style_tags=item.style_tags or [],
            pattern=item.pattern,
            vibe=item.vibe,
            mood=item.mood,
            size=item.size,
            notes=item.notes,
            wear_count=item.wear_count,
            last_worn_at=item.last_worn_at,
            enriched=item.enriched,
            enrichment_data=item.enrichment_data,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
