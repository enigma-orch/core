import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.outfit import Outfit
    from app.models.item import Item


class OutfitItem(BaseModel):
    __tablename__ = "outfit_items"

    outfit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    # Slot this item fills in the outfit: top | bottom | shoes | outerwear | accessory
    role: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Display order in the outfit preview
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    outfit: Mapped["Outfit"] = relationship("Outfit", back_populates="outfit_items")
    item: Mapped["Item"] = relationship("Item")

    __table_args__ = (
        UniqueConstraint("outfit_id", "item_id", name="uq_outfit_items_outfit_item"),
        Index("idx_outfit_items_outfit", "outfit_id"),
        Index("idx_outfit_items_item", "item_id"),
    )
