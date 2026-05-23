"""Shuffle endpoints.

GET  /api/v1/shuffle          — return personalized outfit suggestions.
POST /api/v1/shuffle/prefetch — trigger background pre-generation for the
                                 calling user (returns 202 immediately).

──────────────────────────────────────────────────────────────────────────────
GET /shuffle response strategy
──────────────────────────────────────────────────────────────────────────────

1. Pre-generated (fast path)
   If the hourly prefetch worker has run for this user and the suggestions
   haven't expired, return them directly — they include try-on preview images,
   background colors, and a song suggestion per outfit.
   This path is skipped when the caller passes ?occasion=..., because
   pre-generated suggestions are occasion-neutral.

2. Live fallback (no images)
   When no unexpired suggestions exist (new user, first login, worker hasn't
   run yet), fall back to the existing on-the-fly candidate ranking. This
   path returns item IDs and metadata only — no preview images — but is
   always available.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import AsyncSessionLocal, get_db
from app.models.item import Item
from app.models.outfit_like import OutfitLike
from app.models.outfit_suggestion import OutfitSuggestion
from app.models.spotify import SpotifyTrack
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
    pick_background_color,
    suggest_song,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shuffle", tags=["shuffle"])


async def _taste_signal(db: AsyncSession, user_uuid: uuid.UUID, taste: list[float] | None) -> str:
    if not taste:
        return "none"
    liked = await db.scalar(
        select(func.count()).select_from(OutfitLike).where(OutfitLike.user_id == user_uuid)
    )
    return "liked" if liked else "worn"


async def _spotify_tracks(
    db: AsyncSession, user_uuid: uuid.UUID
) -> list[tuple[str, str, float | None, float | None]] | None:
    try:
        rows = await db.scalars(
            select(SpotifyTrack)
            .where(SpotifyTrack.user_id == user_uuid)
            .order_by(SpotifyTrack.played_at.desc())
            .limit(20)
        )
        return [(t.track_name, t.artist_name, t.valence, t.energy) for t in rows.all()]
    except Exception as exc:
        logger.warning("Spotify track fetch failed for user %s: %s", user_uuid, exc)
        return None


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

    season = current_season()
    outfit_repo = OutfitRepository(db, user_uuid)
    taste = await outfit_repo.get_taste_vector()
    taste_signal = await _taste_signal(db, user_uuid, taste)

    # ── Fast path: pre-generated suggestions with preview images ─────────────
    # Bypassed when the caller specifies an explicit occasion, since pre-generated
    # suggestions are occasion-neutral.
    if not occasion:
        now = datetime.now(timezone.utc)
        pre_rows = (await db.scalars(
            select(OutfitSuggestion)
            .where(
                OutfitSuggestion.user_id == user_uuid,
                OutfitSuggestion.expires_at > now,
            )
            .order_by(OutfitSuggestion.score.desc())
            .limit(limit)
        )).all()

        if pre_rows:
            all_item_ids = [uuid.UUID(i) for row in pre_rows for i in row.item_ids]
            item_map = {
                it.id: it
                for it in (
                    await db.scalars(select(Item).where(Item.id.in_(all_item_ids)))
                ).all()
            }
            suggestions = [
                ShuffleSuggestion(
                    item_ids=[uuid.UUID(i) for i in row.item_ids],
                    items=[
                        ItemOut.model_validate(item_map[uuid.UUID(i)])
                        for i in row.item_ids
                        if uuid.UUID(i) in item_map
                    ],
                    score=round(row.score, 4),
                    occasion=row.occasion,
                    season=row.season,
                    suggested_song=row.suggested_song,
                    preview_image_url=row.preview_image_url,
                    background_color=row.background_color or "#FAFAFA",
                )
                for row in pre_rows
            ]
            return ShuffleResponse(season=season, taste_signal=taste_signal, suggestions=suggestions)

    # ── Live fallback: on-the-fly candidate ranking (no preview images) ───────
    items_rows = await db.scalars(select(Item).where(Item.user_id == user_uuid))
    items = list(items_rows.all())
    if not items:
        raise HTTPException(status_code=400, detail="Wardrobe is empty — upload items first")

    seasonal_items = filter_by_season(items, season) or items

    # Occasion: explicit override > calendar > None
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

    spotify_track_tuples = None
    if user.spotify_id:
        spotify_track_tuples = await _spotify_tracks(db, user_uuid)

    candidates = build_candidates(
        items=seasonal_items,
        taste=taste,
        target_occasion=target_occasion,
        limit=limit,
    )

    suggestions = []
    for c in candidates:
        dominant_vibe = next((it.vibe for it in c.items if it.vibe), None)
        dominant_mood = next((it.mood for it in c.items if it.mood), None)
        suggestions.append(ShuffleSuggestion(
            item_ids=[uuid.UUID(i) for i in c.item_ids],
            items=[ItemOut.model_validate(it) for it in c.items],
            score=round(c.score, 4),
            occasion=target_occasion,
            season=season,
            event_context=event_ctx,
            suggested_song=suggest_song(dominant_mood, dominant_vibe, spotify_track_tuples),
            background_color=pick_background_color(dominant_vibe, target_occasion),
        ))

    return ShuffleResponse(season=season, taste_signal=taste_signal, suggestions=suggestions)


@router.post("/prefetch", status_code=202)
async def trigger_shuffle_prefetch(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> dict:
    """Manually trigger shuffle pre-generation for the calling user.

    Returns 202 immediately. The outfit agent generates a try-on preview for
    each candidate outfit in the background (typically 2–5 minutes depending
    on wardrobe size). Subsequent GET /shuffle calls will return the
    pre-generated results with preview images once the task completes.

    Use this endpoint to prime suggestions after uploading new items without
    waiting for the next hourly cron run.
    """
    user_uuid = uuid.UUID(current_user_id)
    user = await db.get(User, user_uuid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.avatar_url:
        raise HTTPException(
            status_code=400,
            detail="No profile photo on file — upload one first so the try-on agent has a base image.",
        )

    base_url = str(request.base_url).rstrip("/")

    async def _run() -> None:
        from app.workers.shuffle_prefetch import prefetch_for_user
        async with AsyncSessionLocal() as bg_db:
            try:
                bg_user = await bg_db.get(User, user_uuid)
                if bg_user:
                    await prefetch_for_user(bg_user, bg_db, base_url)
                    await bg_db.commit()
            except Exception as exc:
                logger.warning("prefetch background task failed for user %s: %s", user_uuid, exc)

    asyncio.create_task(_run())
    return {"status": "accepted", "message": "Shuffle pre-generation started in the background"}
