"""Pydantic schemas for Outfit requests and responses."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from app.schemas.base import BaseSchema, UUIDSchema


class OutfitIn(BaseSchema):
    item_ids: List[str]
    name: Optional[str] = None
    occasion: Optional[str] = None
    vibe: Optional[str] = None
    mood: Optional[str] = None
    notes: Optional[str] = None


class OutfitOut(UUIDSchema):
    name: Optional[str]
    occasion: Optional[str]
    vibe: Optional[str]
    mood: Optional[str]
    source: str
    wear_count: int
    worn_at: Optional[datetime]
    item_ids: List[str]
    likes_count: int = 0
    liked_by_me: bool = False
    image_url: Optional[str] = None
    created_at: datetime


class OutfitLikeUserOut(BaseSchema):
    id: uuid.UUID
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
