from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScrapedOutfitOut(BaseModel):
    id: uuid.UUID
    image_url: str
    title: str
    brand: str | None = None
    price: float | None = None
    source_url: str
    source_domain: str | None = None
    category: str | None = None
    tags: list[str] = []
    is_liked: bool | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoverBatchResponse(BaseModel):
    outfits: list[ScrapedOutfitOut]
    total: int
    has_more: bool


class LikeOutfitRequest(BaseModel):
    liked: bool


class LikeOutfitResponse(BaseModel):
    id: uuid.UUID
    is_liked: bool
    message: str


class LikedOutfitsResponse(BaseModel):
    outfits: list[ScrapedOutfitOut]
    total: int
