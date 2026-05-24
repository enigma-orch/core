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
    """A single outfit suggestion returned by GET /shuffle.

    Fields:
    - item_ids / items: the wardrobe items that make up the outfit.
    - score: ranking score (higher = better match for the user's taste).
    - occasion: inferred or calendar-derived occasion (nullable).
    - season: current season at generation time.
    - vibe: dominant vibe of the outfit items (nullable).
    - mood: dominant mood of the outfit items (nullable).
    - event_context: populated when the occasion was derived from a calendar
      event (live path only).
    - suggested_song: a song title + artist that fits the outfit's vibe/mood.
    - preview_image_url: AI try-on image URL; null when the user has no avatar
      or when the suggestion was served from the live fallback path before
      image generation completed.
    - background_color: one of the curated palette colors, picked at random
      per suggestion.
    """

    item_ids: List[uuid.UUID]
    items: List[ItemOut] = Field(default_factory=list)
    score: float
    occasion: Optional[str] = None
    season: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    event_context: Optional[EventContext] = None
    suggested_song: Optional[str] = None
    preview_image_url: Optional[str] = None
    background_color: str

    model_config = ConfigDict(from_attributes=True)


class ShuffleResponse(BaseModel):
    """Response envelope for GET /shuffle.

    Fields:
    - season: current season used for wardrobe filtering.
    - taste_signal: how the ranking was personalised — "liked" (user has liked
      outfits), "worn" (based on wear history), or "none" (no signal yet).
    - suggestions: ranked list of outfit suggestions.
    """

    season: str
    taste_signal: str
    suggestions: List[ShuffleSuggestion]
