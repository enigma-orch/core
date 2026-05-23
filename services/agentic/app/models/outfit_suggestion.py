import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class OutfitSuggestion(BaseModel):
    """Pre-generated shuffle suggestion produced by the hourly prefetch worker.

    Keyed on (user_id, expires_at). GET /shuffle reads from this table first
    and falls back to live candidate generation only when no unexpired rows
    exist for the user.

    item_ids is stored as a JSON array of UUID strings so it survives a schema
    migration without needing a join table.
    """

    __tablename__ = "outfit_suggestions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    preview_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    occasion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    vibe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    background_color: Mapped[str] = mapped_column(
        Text, nullable=False, default="#FAFAFA", server_default="'#FAFAFA'"
    )
    suggested_song: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_outfit_suggestions_user_expires", "user_id", "expires_at"),
    )
