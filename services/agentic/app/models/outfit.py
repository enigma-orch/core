import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.outfit_item import OutfitItem
    from app.models.outfit_like import OutfitLike


class Outfit(BaseModel):
    __tablename__ = "outfits"

    # ── Identity ──────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # ── Content ───────────────────────────────────────────────────────────────
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preview_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Context ───────────────────────────────────────────────────────────────
    occasion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    season: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vibe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weather_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Snapshot of Spotify data at generation time:
    # { top_genre, energy, valence, danceability }
    spotify_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ── Source ────────────────────────────────────────────────────────────────
    # 'ai' | 'manual' | 'discovered'
    source: Mapped[str] = mapped_column(Text, nullable=False, default="ai", server_default="ai")

    # ── Feedback & Wear ───────────────────────────────────────────────────────
    rating: Mapped[Optional[int]] = mapped_column(nullable=True)
    worn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    wear_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # ── Vector Embedding ──────────────────────────────────────────────────────
    # Weighted average of all member item embeddings.
    # Each item embedding encodes: category + colors + season + occasion +
    # style_tags + vibe + mood.
    # Used for:
    #   1. Swipe preference learning (push/pull user style vector)
    #   2. Outfit ranking via cosine similarity against user vibe vector
    #   3. Shuffle suggestions — find outfits similar to liked ones
    # NULL until all member items have embeddings.
    # TODO: update VECTOR dims here if switching embedding model
    # TODO: recompute outfit embedding when member items update
    embedding: Mapped[Optional[list]] = mapped_column(Vector(768), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    outfit_items: Mapped[list["OutfitItem"]] = relationship(
        "OutfitItem", back_populates="outfit", cascade="all, delete-orphan"
    )
    likes: Mapped[list["OutfitLike"]] = relationship(
        "OutfitLike", back_populates="outfit", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_outfits_user_id", "user_id"),
        Index("idx_outfits_worn_at", "user_id", "worn_at"),
        Index("idx_outfits_source", "user_id", "source"),
        # HNSW index for cosine similarity ranking and shuffle suggestions.
        # TODO: update VECTOR dims here if switching embedding model
        Index(
            "idx_outfits_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
