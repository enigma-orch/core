import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SpotifyTrack(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "spotify_tracks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Spotify identifiers
    spotify_track_id: Mapped[str] = mapped_column(String(255), nullable=False)
    track_name: Mapped[str] = mapped_column(String(500), nullable=False)
    artist_name: Mapped[str] = mapped_column(String(500), nullable=False)
    album_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    album_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # When the user played it (from Spotify API)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Audio features (fetched separately from Spotify audio-features endpoint)
    valence: Mapped[float | None] = mapped_column(Float, nullable=True)   # 0=negative, 1=positive
    energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    danceability: Mapped[float | None] = mapped_column(Float, nullable=True)
    tempo: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="spotify_tracks")
