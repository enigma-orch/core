import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class OutfitLike(BaseModel):
    __tablename__ = "outfit_likes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    outfit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship("User")
    outfit: Mapped["Outfit"] = relationship("Outfit", back_populates="likes")

    __table_args__ = (
        UniqueConstraint("user_id", "outfit_id", name="uq_outfit_likes_user_outfit"),
        Index("idx_outfit_likes_outfit", "outfit_id"),
        Index("idx_outfit_likes_user", "user_id"),
    )
