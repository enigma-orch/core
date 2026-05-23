import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.outfit import Outfit


class Gallery(BaseModel):
    __tablename__ = "galleries"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    gallery_outfits: Mapped[list["GalleryOutfit"]] = relationship(
        "GalleryOutfit", back_populates="gallery", cascade="all, delete-orphan", order_by="GalleryOutfit.position"
    )

    __table_args__ = (
        Index("idx_galleries_user_id", "user_id"),
        Index("idx_galleries_public", "is_public"),
    )


class GalleryOutfit(BaseModel):
    __tablename__ = "gallery_outfits"

    gallery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("galleries.id", ondelete="CASCADE"), nullable=False)
    outfit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    gallery: Mapped["Gallery"] = relationship("Gallery", back_populates="gallery_outfits")
    outfit: Mapped["Outfit"] = relationship("Outfit")

    __table_args__ = (
        UniqueConstraint("gallery_id", "outfit_id", name="uq_gallery_outfit"),
        Index("idx_gallery_outfits_gallery", "gallery_id"),
        Index("idx_gallery_outfits_outfit", "outfit_id"),
    )
