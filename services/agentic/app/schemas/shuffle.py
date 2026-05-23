"""Pydantic schemas for the shuffle endpoint."""
from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.wardrobe import ItemOut


class EventContext(BaseModel):
    event_title: str
    event_start: Optional[str] = None
    mapped_occasion: Optional[str] = None


class ShuffleSuggestion(BaseModel):
    item_ids: List[uuid.UUID]
    items: List[ItemOut] = Field(default_factory=list)
    score: float
    occasion: Optional[str] = None
    season: Optional[str] = None
    event_context: Optional[EventContext] = None

    model_config = ConfigDict(from_attributes=True)


class ShuffleResponse(BaseModel):
    season: str
    taste_signal: str  # "liked", "worn", or "none"
    suggestions: List[ShuffleSuggestion]
