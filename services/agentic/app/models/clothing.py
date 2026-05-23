"""ClothingItem — a single garment belonging to a user."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ClothingItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clothing_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)   # top | bottom | dress | shoes | bag | outerwear | accessory | jewellery
    colors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    style_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    times_worn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # reverse relation (user → items)
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]
