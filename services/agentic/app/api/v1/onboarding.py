"""Onboarding endpoints — catalog lookups and profile completion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.onboarding import ColorPalette, Store, Vibe
from app.models.user import User
from app.schemas.onboarding import ColorPaletteOut, StoreOut, VibeOut
from app.schemas.user import UserMeOut
from app.services.jwt import get_current_user_id_verified

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── Request schema ────────────────────────────────────────────────────────────

class CompleteProfileRequest(BaseModel):
    # Style preferences (slugs from the catalog endpoints)
    vibes: list[str] = Field(default_factory=list, description="Selected vibe slugs")
    preferred_colors: list[str] = Field(default_factory=list, description="Selected color palette slugs")
    preferred_stores: list[str] = Field(default_factory=list, description="Selected store slugs")

    # Basic profile info collected during onboarding
    display_name: str | None = None
    location: str | None = None
    style_identity: str | None = None

    # Sizing
    tops_size: str | None = None
    bottoms_size: str | None = None
    shoes_size: str | None = None
    outerwear_size: str | None = None

    # Budget
    budget_min: int | None = Field(None, ge=0)
    budget_max: int | None = Field(None, ge=0)


# ── Catalog endpoints ─────────────────────────────────────────────────────────

@router.get("/vibes", response_model=list[VibeOut], summary="List all available style vibes")
async def list_vibes(db: AsyncSession = Depends(get_db)) -> list[VibeOut]:
    rows = await db.scalars(select(Vibe).order_by(Vibe.label))
    return [VibeOut.model_validate(v) for v in rows.all()]


@router.get("/colors", response_model=list[ColorPaletteOut], summary="List all available color palettes")
async def list_color_palettes(db: AsyncSession = Depends(get_db)) -> list[ColorPaletteOut]:
    rows = await db.scalars(select(ColorPalette).order_by(ColorPalette.label))
    return [ColorPaletteOut.model_validate(p) for p in rows.all()]


@router.get("/stores", response_model=list[StoreOut], summary="List all available stores")
async def list_stores(db: AsyncSession = Depends(get_db)) -> list[StoreOut]:
    rows = await db.scalars(select(Store).order_by(Store.name))
    return [StoreOut.model_validate(s) for s in rows.all()]


# ── Profile completion ────────────────────────────────────────────────────────

@router.post(
    "/complete",
    response_model=UserMeOut,
    summary="Complete onboarding — save user style preferences and profile info",
)
async def complete_onboarding(
    body: CompleteProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> UserMeOut:
    user = await db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.vibes:
        user.preferred_styles = body.vibes
    if body.preferred_colors:
        user.preferred_colors = body.preferred_colors
    if body.preferred_stores:
        user.preferred_stores = body.preferred_stores

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.location is not None:
        user.location = body.location
    if body.style_identity is not None:
        user.style_identity = body.style_identity
    if body.tops_size is not None:
        user.tops_size = body.tops_size
    if body.bottoms_size is not None:
        user.bottoms_size = body.bottoms_size
    if body.shoes_size is not None:
        user.shoes_size = body.shoes_size
    if body.outerwear_size is not None:
        user.outerwear_size = body.outerwear_size
    if body.budget_min is not None:
        user.budget_min = body.budget_min
    if body.budget_max is not None:
        user.budget_max = body.budget_max

    await db.flush()
    await db.refresh(user)
    return UserMeOut.from_user(user)
