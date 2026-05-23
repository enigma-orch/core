"""GET /home/feed and GET /outfits/today — home dashboard endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.home import HomeFeedOut, TodaysPickOut
from app.services.home_feed import (
    build_greeting,
    get_discover_mix,
    get_more_for_today,
    get_or_build_todays_pick,
    get_style_pulse,
)
from app.services.jwt import get_current_user_id_verified
from app.services.weather import get_weather

logger = logging.getLogger(__name__)

router = APIRouter(tags=["home"])


@router.get("/outfits/today", response_model=TodaysPickOut)
async def todays_pick(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> TodaysPickOut:
    user = await db.get(User, uuid.UUID(current_user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    weather = await get_weather(user.location)
    return await get_or_build_todays_pick(db, user, weather)


@router.get("/home/feed", response_model=HomeFeedOut)
async def home_feed(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> HomeFeedOut:
    user = await db.get(User, uuid.UUID(current_user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    weather = await get_weather(user.location)

    # Today's pick may write (cache + persist outfit), so do it first sequentially.
    try:
        pick = await get_or_build_todays_pick(db, user, weather)
    except Exception as exc:
        logger.exception("todays_pick failed for user %s: %s", user.id, exc)
        pick = None

    # Sequential — sharing one AsyncSession across asyncio.gather is unsafe.
    # The queries are cheap; latency budget is fine.
    from app.schemas.social import StylePulseOut

    try:
        pulse = await get_style_pulse(db, user.id)
    except Exception as exc:
        logger.warning("style_pulse failed: %s", exc)
        pulse = StylePulseOut()

    try:
        more_cards = await get_more_for_today(
            db, user, weather, exclude_outfit_id=(pick.outfit_id if pick else None)
        )
    except Exception as exc:
        logger.warning("more_for_today failed: %s", exc)
        more_cards = []

    try:
        discover = await get_discover_mix(db, user.id, limit=10)
    except Exception as exc:
        logger.warning("discover_mix failed: %s", exc)
        discover = []

    return HomeFeedOut(
        greeting=build_greeting(user),
        todays_pick=pick,
        style_pulse=pulse,
        more_for_today=more_cards,
        discover=discover,
    )
