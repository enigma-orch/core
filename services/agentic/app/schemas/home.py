from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.discover import ScrapedOutfitOut
from app.schemas.social import StylePulseOut


class WeatherOut(BaseModel):
    condition: str
    temperature_c: float
    is_rainy: bool
    is_cold: bool
    is_hot: bool
    tags: list[str] = []


class TodaysPickOut(BaseModel):
    outfit_id: uuid.UUID | None = None
    image_url: str | None = None
    title: str | None = None
    occasion: str | None = None
    vibe: str | None = None
    mood: str | None = None
    item_ids: list[str] = []
    reason: str
    spotify_context: dict[str, Any] | None = None
    weather: WeatherOut | None = None
    pick_date: datetime | None = None


class OutfitCardOut(BaseModel):
    """Lightweight card for 'More for today' tiles."""
    id: str | None = None
    eyebrow: str
    title: str
    image_url: str | None = None
    tint_hex: str | None = None
    item_ids: list[str] = []


class HomeFeedOut(BaseModel):
    greeting: str
    todays_pick: TodaysPickOut | None = None
    style_pulse: StylePulseOut
    more_for_today: list[OutfitCardOut] = []
    discover: list[ScrapedOutfitOut] = []
