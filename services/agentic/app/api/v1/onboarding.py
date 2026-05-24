"""Onboarding endpoints — catalog lookups and profile completion.

Catalog endpoints (no auth required):
  GET /onboarding/vibes   — style vibes the user picks during onboarding
  GET /onboarding/colors  — color palette options
  GET /onboarding/stores  — supported stores
  GET /onboarding/sizes   — available sizes grouped by category (tops, bottoms,
                            shoes, outerwear); use the slug values when calling
                            POST /onboarding/complete

Profile completion (auth required):
  POST /onboarding/complete — persist all onboarding choices in one shot;
                              idempotent, safe to call multiple times.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.onboarding import ColorPalette, Size, Store, Vibe
from app.models.user import User
from app.schemas.onboarding import ColorPaletteOut, SizeCatalogOut, SizeOut, StoreOut, VibeOut
from app.schemas.user import UserMeOut
from app.services.jwt import get_current_user_id_verified

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── Request schema ────────────────────────────────────────────────────────────

class CompleteProfileRequest(BaseModel):
    """All fields are optional — only supplied fields are updated.

    Slugs for vibes, preferred_colors, and preferred_stores come from the
    corresponding catalog endpoints. Slugs for size fields come from
    GET /onboarding/sizes (e.g. "tops-m", "bottoms-32", "shoes-42").
    """

    # Style preferences (slugs from catalog endpoints)
    vibes: list[str] = Field(
        default_factory=list,
        description="Vibe slugs from GET /onboarding/vibes (e.g. ['streetwear', 'minimal']).",
    )
    preferred_colors: list[str] = Field(
        default_factory=list,
        description="Color palette slugs from GET /onboarding/colors (e.g. ['earth-tones']).",
    )
    preferred_stores: list[str] = Field(
        default_factory=list,
        description="Store slugs from GET /onboarding/stores (e.g. ['zara', 'asos']).",
    )

    # Basic profile info
    display_name: str | None = Field(None, description="Public display name.")
    location: str | None = Field(None, description="City or region (used for weather context).")
    style_identity: str | None = Field(None, description="Free-text style self-description.")

    # Sizing — slugs from GET /onboarding/sizes
    tops_size: str | None = Field(
        None,
        description="Tops size slug from GET /onboarding/sizes (e.g. 'tops-m').",
    )
    bottoms_size: str | None = Field(
        None,
        description="Bottoms size slug from GET /onboarding/sizes (e.g. 'bottoms-32').",
    )
    shoes_size: str | None = Field(
        None,
        description="Shoes size slug from GET /onboarding/sizes (e.g. 'shoes-42').",
    )
    outerwear_size: str | None = Field(
        None,
        description="Outerwear size slug from GET /onboarding/sizes (e.g. 'outerwear-l').",
    )

    # Budget
    budget_min: int | None = Field(None, ge=0, description="Minimum budget in USD.")
    budget_max: int | None = Field(None, ge=0, description="Maximum budget in USD.")


# ── Catalog endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/vibes",
    response_model=list[VibeOut],
    summary="List all style vibes",
    description="Returns every available vibe in alphabetical order. Pass the selected slugs to POST /onboarding/complete.",
)
async def list_vibes(db: AsyncSession = Depends(get_db)) -> list[VibeOut]:
    rows = await db.scalars(select(Vibe).order_by(Vibe.label))
    return [VibeOut.model_validate(v) for v in rows.all()]


@router.get(
    "/colors",
    response_model=list[ColorPaletteOut],
    summary="List all color palettes",
    description="Returns every color palette with its swatch hex values. Pass the selected slugs to POST /onboarding/complete.",
)
async def list_color_palettes(db: AsyncSession = Depends(get_db)) -> list[ColorPaletteOut]:
    rows = await db.scalars(select(ColorPalette).order_by(ColorPalette.label))
    return [ColorPaletteOut.model_validate(p) for p in rows.all()]


@router.get(
    "/stores",
    response_model=list[StoreOut],
    summary="List all supported stores",
    description="Returns every store the user can select as a preferred shopping destination. Pass the selected slugs to POST /onboarding/complete.",
)
async def list_stores(db: AsyncSession = Depends(get_db)) -> list[StoreOut]:
    rows = await db.scalars(select(Store).order_by(Store.name))
    return [StoreOut.model_validate(s) for s in rows.all()]


@router.get(
    "/sizes",
    response_model=SizeCatalogOut,
    summary="List all available sizes grouped by category",
    description=(
        "Returns sizes grouped into four categories: **tops** (S–2XL), "
        "**bottoms** (waist 28–44), **shoes** (8–28), and **outerwear** (S–2XL). "
        "Use the `slug` values when submitting sizes via POST /onboarding/complete."
    ),
)
async def list_sizes(db: AsyncSession = Depends(get_db)) -> SizeCatalogOut:
    rows = (await db.scalars(select(Size).order_by(Size.category, Size.sort_order))).all()
    grouped: dict[str, list[SizeOut]] = {"tops": [], "bottoms": [], "shoes": [], "outerwear": []}
    for row in rows:
        if row.category in grouped:
            grouped[row.category].append(SizeOut.model_validate(row))
    return SizeCatalogOut(**grouped)


# ── Profile completion ────────────────────────────────────────────────────────

@router.post(
    "/complete",
    response_model=UserMeOut,
    summary="Complete onboarding",
    description=(
        "Persists all onboarding choices for the authenticated user in a single request. "
        "Only fields explicitly provided are updated — omitted fields are left unchanged. "
        "Safe to call multiple times (idempotent per field)."
    ),
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
