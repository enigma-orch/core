from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class FollowOut(BaseModel):
    user_id: uuid.UUID
    display_name: str | None = None
    avatar_url: str | None = None
    location: str | None = None
    followed_at: datetime

    model_config = {"from_attributes": True}


class FriendOutfitPreview(BaseModel):
    user_id: uuid.UUID
    user_name: str | None = None
    user_avatar_url: str | None = None
    location: str | None = None
    outfit_id: uuid.UUID
    preview_image_url: str | None = None
    vibe: str | None = None
    occasion: str | None = None
    worn_at: datetime | None = None


class StylePulseOut(BaseModel):
    cities: dict[str, list[FriendOutfitPreview]] = {}
    friends: list[FriendOutfitPreview] = []
    total: int = 0
