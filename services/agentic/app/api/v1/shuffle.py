"""GET /api/v1/shuffle — personalized outfit suggestions from the wardrobe."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.item import Item
from app.models.user import User
from app.repositories.outfit import OutfitRepository
from app.schemas.shuffle import EventContext, ShuffleResponse, ShuffleSuggestion
from app.schemas.wardrobe import ItemOut
from app.services import google_calendar as gcal_svc
from app.services.jwt import get_current_user_id_verified
from app.services.shuffle import (
    build_candidates,
    current_season,
    filter_by_season,
    occasion_from_event_title,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shuffle", tags=["shuffle"])


@router.get("", response_model=ShuffleResponse)
async def shuffle_outfits(
    occasion: str | None = Query(
        None,
        description="Override the inferred occasion (casual, smart-casual, formal, party, activewear, streetwear).",
    ),
    limit: int = Query(5, ge=1, le=10),
    use_calendar: bool = Query(
        True,
        description="If the user has Google Calendar linked, derive occasion from the next event.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> ShuffleResponse:
    user_uuid = uuid.UUID(current_user_id)
    user = await db.get(User, user_uuid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # ── Inputs ────────────────────────────────────────────────────────────────
    items_rows = await db.scalars(select(Item).where(Item.user_id == user_uuid))
    items = list(items_rows.all())
    if not items:
        raise HTTPException(status_code=400, detail="Wardrobe is empty — upload items first")

    season = current_season()
    seasonal_items = filter_by_season(items, season) or items

    outfit_repo = OutfitRepository(db, user_uuid)
    taste = await outfit_repo.get_taste_vector()
    taste_signal = "none"
    if taste:
        # Best-effort label of where the signal came from. We re-check via
        # a count query so the response is honest about the source.
        from sqlalchemy import func
        from app.models.outfit_like import OutfitLike
        liked = await db.scalar(
            select(func.count()).select_from(OutfitLike).where(OutfitLike.user_id == user_uuid)
        )
        taste_signal = "liked" if liked else "worn"

    # ── Occasion: explicit override > calendar lookup > None ─────────────────
    event_ctx: EventContext | None = None
    target_occasion = occasion
    if not target_occasion and use_calendar and user.google_access_token:
        try:
            events = await gcal_svc.list_upcoming_events(
                user.google_access_token,
                calendar_id=user.google_calendar_id or "primary",
                max_results=5,
            )
        except Exception as exc:
            logger.warning("Calendar lookup failed for user %s: %s", user_uuid, exc)
            events = []
        for ev in events:
            mapped = occasion_from_event_title(ev.get("summary"))
            if mapped:
                target_occasion = mapped
                event_ctx = EventContext(
                    event_title=ev.get("summary") or "",
                    event_start=(ev.get("start") or {}).get("dateTime")
                    or (ev.get("start") or {}).get("date"),
                    mapped_occasion=mapped,
                )
                break

    # ── Candidate generation ─────────────────────────────────────────────────
    candidates = build_candidates(
        items=seasonal_items,
        taste=taste,
        target_occasion=target_occasion,
        limit=limit,
    )

    suggestions = [
        ShuffleSuggestion(
            item_ids=[uuid.UUID(i) for i in c.item_ids],
            items=[ItemOut.model_validate(it) for it in c.items],
            score=round(c.score, 4),
            occasion=target_occasion,
            season=season,
            event_context=event_ctx,
        )
        for c in candidates
    ]

    return ShuffleResponse(
        season=season,
        taste_signal=taste_signal,
        suggestions=suggestions,
    )
