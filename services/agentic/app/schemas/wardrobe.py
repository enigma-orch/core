import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ── Standalone background removal ─────────────────────────────────────────────

class RemoveBackgroundResponse(BaseModel):
    url: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


# ── Agent detection schemas (Gemini response structure) ───────────────────────

class DetectedClothingItem(BaseModel):
    name: str
    category: Literal["top", "bottom", "dress", "shoes", "bag", "outerwear", "accessory", "jewellery"]
    subcategory: str
    colors: List[str] = Field(default_factory=list)
    brand: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    season: List[str] = Field(default_factory=list)
    occasion: Literal["casual", "smart-casual", "formal", "streetwear", "activewear", "party"]
    pattern: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    size: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    search_query: str


class DetectedOutfit(BaseModel):
    name: Optional[str] = None
    summary: Optional[str] = None
    mood: Optional[str] = None
    vibe: Optional[str] = None
    season: Optional[str] = None
    occasion: Optional[str] = None
    items: List[DetectedClothingItem] = Field(default_factory=list)


# ── DB output schemas ─────────────────────────────────────────────────────────

class ItemWithEmbeddingOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    original_image_url: Optional[str] = None
    clean_image_url: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    colors: Optional[List[str]] = None
    season: Optional[List[str]] = None
    occasion: Optional[str] = None
    style_tags: Optional[List[str]] = None
    pattern: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    size: Optional[str] = None
    enriched: bool
    enrichment_data: Optional[dict] = None
    embedding: Optional[List[float]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutfitWithItemsOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: Optional[str] = None
    preview_image_url: Optional[str] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    source: str
    embedding: Optional[List[float]] = None
    items: List[ItemWithEmbeddingOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Upload response (no embedding, includes both image URLs) ──────────────────

class ItemUploadOut(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    colors: Optional[List[str]] = None
    season: Optional[List[str]] = None
    occasion: Optional[str] = None
    style_tags: Optional[List[str]] = None
    pattern: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    size: Optional[str] = None
    enrichment_data: Optional[dict] = None
    original_image_url: Optional[str] = None
    clean_image_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Outfit composition ───────────────────────────────────────────────────────

class OutfitComposeRequest(BaseModel):
    item_ids: List[uuid.UUID] = Field(default_factory=list)
    user_image_url: str


class ItemOut(BaseModel):
    """Public item shape — no embedding."""

    id: uuid.UUID
    user_id: uuid.UUID
    original_image_url: Optional[str] = None
    clean_image_url: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    colors: Optional[List[str]] = None
    season: Optional[List[str]] = None
    occasion: Optional[str] = None
    style_tags: Optional[List[str]] = None
    pattern: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    size: Optional[str] = None
    enriched: bool
    enrichment_data: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutfitComposeOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: Optional[str] = None
    preview_image_url: Optional[str] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    source: str
    items: List[ItemOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
