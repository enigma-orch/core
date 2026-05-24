import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field

from app.models.user import MoodEnum
from app.schemas.onboarding import ColorPaletteOut, StoreOut, VibeOut


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


class UserMeOut(BaseModel):
    # Identity
    id: uuid.UUID
    email: str | None
    display_name: str | None
    avatar_url: str | None

    # Mood
    mood: MoodEnum

    # Style preferences
    location: str | None
    style_identity: str | None
    preferred_styles: list[str] | None
    preferred_colors: list[str] | None
    preferred_stores: list[str] | None
    budget_min: int | None
    budget_max: int | None

    # Sizing
    tops_size: str | None
    bottoms_size: str | None
    shoes_size: str | None
    outerwear_size: str | None

    # Connected integrations (presence only — no tokens)
    spotify_id: str | None
    has_spotify: bool
    has_google_calendar: bool
    google_calendar_id: str | None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user: object) -> "UserMeOut":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            mood=user.mood,
            location=user.location,
            style_identity=user.style_identity,
            preferred_styles=user.preferred_styles,
            preferred_colors=user.preferred_colors,
            preferred_stores=user.preferred_stores,
            budget_min=user.budget_min,
            budget_max=user.budget_max,
            tops_size=user.tops_size,
            bottoms_size=user.bottoms_size,
            shoes_size=user.shoes_size,
            outerwear_size=user.outerwear_size,
            spotify_id=user.spotify_id,
            has_spotify=user.spotify_id is not None,
            has_google_calendar=user.google_access_token is not None,
            google_calendar_id=user.google_calendar_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class AuthMeOut(BaseModel):
    """Full user context returned by GET /auth/me.

    Extends UserMeOut with resolved vibe, color palette, and store objects
    (instead of raw slug arrays) so the client never needs a second request
    to display the user's profile.
    """
    # Identity
    id: uuid.UUID
    email: str | None
    display_name: str | None
    avatar_url: str | None

    # Mood
    mood: MoodEnum

    # Style preferences — full objects
    vibes: list[VibeOut]
    color_palettes: list[ColorPaletteOut]
    stores: list[StoreOut]

    # Style preferences — raw slugs (kept for completeness)
    preferred_styles: list[str] | None
    preferred_colors: list[str] | None
    preferred_stores: list[str] | None

    # Free-text style fields
    location: str | None
    style_identity: str | None

    # Sizing
    tops_size: str | None
    bottoms_size: str | None
    shoes_size: str | None
    outerwear_size: str | None

    # Budget
    budget_min: int | None
    budget_max: int | None

    # Connected integrations (presence only — no tokens exposed)
    spotify_id: str | None
    has_spotify: bool
    has_google_calendar: bool
    google_calendar_id: str | None

    # Timestamps
    created_at: datetime
    updated_at: datetime


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
