import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Item(BaseModel):
    __tablename__ = "items"

    # ── Identity ──────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # ── Source Images ─────────────────────────────────────────────────────────
    original_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clean_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Core Metadata (all optional — enrichment agent fills progressively) ───
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Style Attributes ──────────────────────────────────────────────────────
    colors: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    season: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    occasion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    style_tags: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vibe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Physical Attributes (user fills manually) ─────────────────────────────
    size: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Wear Tracking ─────────────────────────────────────────────────────────
    wear_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_worn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Enrichment State ──────────────────────────────────────────────────────
    enriched: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    enrichment_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ── Vector Embedding ──────────────────────────────────────────────────────
    # Encodes: category + colors + season + occasion + style_tags + vibe + mood
    # Used for cosine similarity in outfit shuffling and recommendation.
    # NULL until enrichment completes.
    # TODO: update VECTOR dims here if switching embedding model
    embedding: Mapped[Optional[list]] = mapped_column(Vector(768), nullable=True)

    __table_args__ = (
        Index("idx_items_user_id", "user_id"),
        Index("idx_items_category", "user_id", "category"),
        Index("idx_items_last_worn", "user_id", "last_worn_at"),
        # HNSW index for cosine similarity search via pgvector.
        # HNSW gives better recall than ivfflat on small/growing per-user
        # tables without needing a tuned `lists` parameter.
        Index(
            "idx_items_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
