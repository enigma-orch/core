"""Home feed helpers shared by /home/feed and /outfits/today."""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_pick import DailyOutfitPick
from app.models.follow import Follow
from app.models.item import Item
from app.models.outfit import Outfit
from app.models.outfit_item import OutfitItem
from app.models.scraped_outfit import ScrapedOutfit
from app.models.user import User
from app.repositories.outfit import OutfitRepository
from app.schemas.discover import ScrapedOutfitOut
from app.schemas.home import OutfitCardOut, TodaysPickOut, WeatherOut
from app.schemas.social import FriendOutfitPreview, StylePulseOut
from app.services.shuffle import (
    ShuffleCandidate,
    build_candidates,
    current_season,
    filter_by_season,
)
from app.services.weather import Weather, get_weather

logger = logging.getLogger(__name__)


# Map a (mood, weather_bucket) to a target occasion that the shuffle scorer
# already understands. Kept intentionally small and deterministic.
_MOOD_OCCASION: dict[str, str] = {
    "happy": "casual",
    "energetic": "activewear",
    "calm": "smart-casual",
    "relaxed": "casual",
    "focused": "smart-casual",
    "melancholic": "casual",
    "sad": "casual",
    "angry": "streetwear",
    "unknown": "casual",
}


def _mood_to_occasion(mood: str | None, weather: Weather | None) -> str:
    base = _MOOD_OCCASION.get((mood or "unknown").lower(), "casual")
    if weather and weather.is_rainy and base != "activewear":
        return "smart-casual"
    return base


def _weather_out(weather: Weather | None) -> WeatherOut | None:
    if not weather:
        return None
    return WeatherOut(
        condition=weather.condition,
        temperature_c=weather.temperature_c,
        is_rainy=weather.is_rainy,
        is_cold=weather.is_cold,
        is_hot=weather.is_hot,
        tags=weather.tags,
    )


def _build_reason(mood: str, weather: Weather | None) -> str:
    if not weather:
        return f"Tuned to your {mood} mood."
    if weather.is_rainy:
        return f"Picked for a {weather.condition} day — keeping your {mood} vibe dry."
    if weather.is_cold:
        return f"Cold ({round(weather.temperature_c)}°) outside — layered up for your {mood} mood."
    if weather.is_hot:
        return f"Warm ({round(weather.temperature_c)}°) — light look matched to your {mood} mood."
    return f"Mild day — leaning into your {mood} mood."


async def _latest_spotify_context(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    row = await db.scalar(
        select(Outfit.spotify_context)
        .where(Outfit.user_id == user_id, Outfit.spotify_context.is_not(None))
        .order_by(Outfit.created_at.desc())
        .limit(1)
    )
    return row if isinstance(row, dict) else None


async def _persist_daily_pick(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    outfit_id: uuid.UUID,
    reason: str,
    spotify_context: dict | None,
    weather: Weather | None,
) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(DailyOutfitPick.__table__).values(
        user_id=user_id,
        pick_date=date.today(),
        outfit_id=outfit_id,
        spotify_context=spotify_context,
        weather_snapshot={
            "condition": weather.condition,
            "temperature_c": weather.temperature_c,
            "is_rainy": weather.is_rainy,
            "tags": weather.tags,
        } if weather else None,
        reason=reason,
    ).on_conflict_do_nothing(index_elements=["user_id", "pick_date"])
    await db.execute(stmt)


async def _persist_pick_outfit(
    db: AsyncSession,
    user_id: uuid.UUID,
    candidate: ShuffleCandidate,
    *,
    mood: str,
    occasion: str,
    weather: Weather | None,
    spotify_context: dict | None,
) -> Outfit:
    """Materialize a shuffle candidate as a row in `outfits` so the daily pick has an FK target."""
    preview_url = next(
        (it.clean_image_url or it.original_image_url for it in candidate.items if it.original_image_url),
        None,
    )
    outfit = Outfit(
        user_id=user_id,
        name=" & ".join((it.name or it.category or "piece") for it in candidate.items[:2]) or "Today's Pick",
        preview_image_url=preview_url,
        occasion=occasion,
        season=current_season(),
        vibe=candidate.items[0].vibe if candidate.items else None,
        mood=mood,
        weather_context=weather.condition if weather else None,
        spotify_context=spotify_context,
        source="daily_pick",
        # Daily pick *is* what they're wearing today — surface it in style-pulse.
        worn_at=datetime.now(timezone.utc),
        wear_count=1,
    )
    db.add(outfit)
    await db.flush()
    for position, item in enumerate(candidate.items):
        db.add(OutfitItem(outfit_id=outfit.id, item_id=item.id, position=position))
    await db.flush()
    return outfit


async def get_or_build_todays_pick(
    db: AsyncSession,
    user: User,
    weather: Weather | None = None,
) -> TodaysPickOut:
    if weather is None:
        weather = await get_weather(user.location)

    # 1) cache lookup
    cached = (
        await db.execute(
            select(DailyOutfitPick, Outfit)
            .join(Outfit, Outfit.id == DailyOutfitPick.outfit_id)
            .where(
                DailyOutfitPick.user_id == user.id,
                DailyOutfitPick.pick_date == date.today(),
            )
        )
    ).first()
    if cached:
        pick, outfit = cached
        item_ids = [
            str(oi.item_id)
            for oi in (
                await db.scalars(
                    select(OutfitItem).where(OutfitItem.outfit_id == outfit.id).order_by(OutfitItem.position)
                )
            ).all()
        ]
        return TodaysPickOut(
            outfit_id=outfit.id,
            image_url=outfit.preview_image_url,
            title=outfit.name,
            occasion=outfit.occasion,
            vibe=outfit.vibe,
            mood=outfit.mood,
            item_ids=item_ids,
            reason=pick.reason or _build_reason(outfit.mood or "unknown", weather),
            spotify_context=pick.spotify_context,
            weather=_weather_out(weather),
            pick_date=pick.created_at,
        )

    # 2) miss — build from wardrobe via shuffle
    spotify_context = await _latest_spotify_context(db, user.id)
    mood = (user.mood.value if hasattr(user.mood, "value") else str(user.mood or "unknown")).lower()
    target_occasion = _mood_to_occasion(mood, weather)

    items = list(
        (await db.scalars(select(Item).where(Item.user_id == user.id))).all()
    )
    if items:
        seasonal = filter_by_season(items, current_season()) or items
        repo = OutfitRepository(db, user.id)
        taste = await repo.get_taste_vector()
        candidates = build_candidates(seasonal, taste, target_occasion, limit=1)
        if candidates:
            cand = candidates[0]
            outfit_row = await _persist_pick_outfit(
                db, user.id, cand,
                mood=mood, occasion=target_occasion,
                weather=weather, spotify_context=spotify_context,
            )
            reason = _build_reason(mood, weather)
            await _persist_daily_pick(
                db, user.id,
                outfit_id=outfit_row.id, reason=reason,
                spotify_context=spotify_context, weather=weather,
            )
            await db.commit()
            return TodaysPickOut(
                outfit_id=outfit_row.id,
                image_url=outfit_row.preview_image_url,
                title=outfit_row.name,
                occasion=outfit_row.occasion,
                vibe=outfit_row.vibe,
                mood=outfit_row.mood,
                item_ids=[str(i.id) for i in cand.items],
                reason=reason,
                spotify_context=spotify_context,
                weather=_weather_out(weather),
                pick_date=datetime.now(timezone.utc),
            )

    # 3) fallback — pick a recent liked scraped outfit so the card never shows empty
    fallback = await db.scalar(
        select(ScrapedOutfit)
        .where(ScrapedOutfit.user_id == user.id)
        .order_by(ScrapedOutfit.is_liked.desc().nullslast(), ScrapedOutfit.created_at.desc())
        .limit(1)
    )
    return TodaysPickOut(
        outfit_id=None,
        image_url=fallback.image_url if fallback else None,
        title=fallback.title if fallback else "Add wardrobe items to unlock today's pick",
        occasion=fallback.category if fallback else None,
        vibe=None,
        mood=mood,
        item_ids=[],
        reason=_build_reason(mood, weather),
        spotify_context=spotify_context,
        weather=_weather_out(weather),
        pick_date=datetime.now(timezone.utc),
    )


async def get_more_for_today(
    db: AsyncSession, user: User, weather: Weather | None, exclude_outfit_id: uuid.UUID | None
) -> list[OutfitCardOut]:
    mood = (user.mood.value if hasattr(user.mood, "value") else str(user.mood or "unknown")).lower()
    target_occasion = _mood_to_occasion(mood, weather)

    items = list((await db.scalars(select(Item).where(Item.user_id == user.id))).all())
    if not items:
        return []
    seasonal = filter_by_season(items, current_season()) or items
    repo = OutfitRepository(db, user.id)
    taste = await repo.get_taste_vector()
    candidates = build_candidates(seasonal, taste, target_occasion, limit=5)

    cards: list[OutfitCardOut] = []
    for c in candidates:
        first = c.items[0] if c.items else None
        if not first:
            continue
        cards.append(OutfitCardOut(
            id=",".join(c.item_ids),
            eyebrow=f"{target_occasion.title()} · {current_season().title()}",
            title=first.name or "Curated look",
            image_url=first.clean_image_url or first.original_image_url,
            tint_hex=None,
            item_ids=list(c.item_ids),
        ))
        if len(cards) >= 4:
            break
    return cards


async def get_discover_mix(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 10
) -> list[ScrapedOutfitOut]:
    """Latest unseen mix of social + retail scraped outfits."""
    rows = (
        await db.scalars(
            select(ScrapedOutfit)
            .where(
                ScrapedOutfit.user_id == user_id,
                ScrapedOutfit.is_liked.is_(None),
            )
            .order_by(ScrapedOutfit.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [ScrapedOutfitOut.model_validate(r) for r in rows]


async def get_style_pulse(
    db: AsyncSession, user_id: uuid.UUID, days: int = 7, limit: int = 20
) -> StylePulseOut:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(Outfit, User)
            .join(Follow, Follow.followee_id == Outfit.user_id)
            .join(User, User.id == Outfit.user_id)
            .where(
                Follow.follower_id == user_id,
                Outfit.worn_at.is_not(None),
                Outfit.worn_at >= since,
            )
            .order_by(Outfit.worn_at.desc())
            .limit(limit)
        )
    ).all()

    friends: list[FriendOutfitPreview] = []
    cities: dict[str, list[FriendOutfitPreview]] = {}
    for outfit, user in rows:
        preview = FriendOutfitPreview(
            user_id=user.id,
            user_name=user.display_name,
            user_avatar_url=user.avatar_url,
            location=user.location,
            outfit_id=outfit.id,
            preview_image_url=outfit.preview_image_url,
            vibe=outfit.vibe,
            occasion=outfit.occasion,
            worn_at=outfit.worn_at,
        )
        friends.append(preview)
        city = (user.location or "Unknown").split(",")[0].strip()
        cities.setdefault(city, []).append(preview)

    return StylePulseOut(cities=cities, friends=friends, total=len(friends))


def build_greeting(user: User) -> str:
    name = (user.display_name or "").strip()
    first = name.split(" ")[0] if name else "you"
    return f"hey, {first}"
