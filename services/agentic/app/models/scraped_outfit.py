from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ScrapedOutfit(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scraped_outfits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Feedback
    is_liked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Style/weather context used when this was scraped
    style_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)
    weather_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)

    user: Mapped["User"] = relationship(back_populates="scraped_outfits")
