import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.user import MoodEnum


class UserOut(BaseModel):
    id: uuid.UUID
    email: str | None
    display_name: str | None
    avatar_url: str | None
    mood: MoodEnum
    spotify_id: str | None
    google_calendar_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 3600  # seconds
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserMoodUpdate(BaseModel):
    mood: MoodEnum
