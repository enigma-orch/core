import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.types import EncryptedString


class MoodEnum(str, enum.Enum):
    HAPPY = "happy"
    SAD = "sad"
    ENERGETIC = "energetic"
    CALM = "calm"
    MELANCHOLIC = "melancholic"
    ANGRY = "angry"
    RELAXED = "relaxed"
    FOCUSED = "focused"
    UNKNOWN = "unknown"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Current detected mood
    mood: Mapped[MoodEnum] = mapped_column(
        Enum(MoodEnum, name="mood_enum"), default=MoodEnum.UNKNOWN, nullable=False
    )

    # --- Style Preferences (for discover/scraping) ---
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    style_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_styles: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)
    preferred_colors: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)
    preferred_stores: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)
    budget_min: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True, default=500)
    tops_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bottoms_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shoes_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    outerwear_size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # --- Spotify OAuth ---
    spotify_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    spotify_access_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    spotify_refresh_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    spotify_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Google Calendar OAuth ---
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    google_access_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    google_refresh_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    google_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    google_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- App refresh token (SHA-256 hash of the issued token) ---
    refresh_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    spotify_tracks: Mapped[list["SpotifyTrack"]] = relationship(
        "SpotifyTrack", back_populates="user", cascade="all, delete-orphan"
    )
    items: Mapped[list["Item"]] = relationship(  # type: ignore[name-defined]
        "Item", cascade="all, delete-orphan"
    )
    outfits: Mapped[list["Outfit"]] = relationship(  # type: ignore[name-defined]
        "Outfit", cascade="all, delete-orphan"
    )
    scraped_outfits: Mapped[list["ScrapedOutfit"]] = relationship(
        "ScrapedOutfit", back_populates="user", cascade="all, delete-orphan"
    )
