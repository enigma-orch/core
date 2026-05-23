from app.schemas.user import TokenResponse, UserOut, UserMoodUpdate
from app.schemas.wardrobe import (
    DetectedClothingItem,
    DetectedOutfit,
    ErrorResponse,
    ItemOut,
    ItemWithEmbeddingOut,
    OutfitWithItemsOut,
    RemoveBackgroundResponse,
)
from app.schemas.clothing import ClothingItemIn, ClothingItemOut
from app.schemas.outfit import OutfitIn, OutfitOut, OutfitLikeUserOut

__all__ = [
    # user
    "TokenResponse", "UserOut", "UserMoodUpdate",
    # wardrobe
    "DetectedClothingItem", "DetectedOutfit", "ErrorResponse",
    "ItemOut", "ItemWithEmbeddingOut", "OutfitWithItemsOut",
    "RemoveBackgroundResponse",
    # clothing items
    "ClothingItemIn", "ClothingItemOut",
    # outfits
    "OutfitIn", "OutfitOut", "OutfitLikeUserOut",
]
