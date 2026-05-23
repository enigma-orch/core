from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.scraped_outfit import ScrapedOutfit
from app.models.user import User
from app.schemas.discover import (
    DiscoverBatchResponse,
    LikeOutfitRequest,
    LikeOutfitResponse,
    LikedOutfitsResponse,
    ScrapedOutfitOut,
)
from app.services.outfit_scraper import DEV_OUTFITS, scrape_outfits_for_user
from app.services.weather import get_weather
from app.services.jwt import get_current_user_id

router = APIRouter(prefix="/discover", tags=["discover"])

BATCH_SIZE = 10


async def _fetch_unseen(uid: uuid.UUID, db: AsyncSession) -> list[ScrapedOutfit]:
    rows = await db.scalars(
        select(ScrapedOutfit)
        .where(ScrapedOutfit.user_id == uid, ScrapedOutfit.is_liked.is_(None))
        .order_by(ScrapedOutfit.created_at.desc())
        .limit(BATCH_SIZE + 1)
    )
    return list(rows.all())


async def _seed_real_outfits(uid: uuid.UUID) -> None:
    """Background task: scrape real outfits after dev outfits are seeded."""
    from app.infrastructure.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        user = await session.get(User, uid)
        if not user:
            return
        weather = await get_weather(user.location)
        added = await scrape_outfits_for_user(user, session, weather)
        if added > 0:
            await session.commit()


async def _seed_dev_outfits(uid: uuid.UUID, db: AsyncSession) -> int:
    """Immediately seed static dev outfits for a new user — no HTTP calls, instant."""
    existing = set(
        (await db.scalars(
            select(ScrapedOutfit.image_url).where(ScrapedOutfit.user_id == uid)
        )).all()
    )
    added = 0
    for data in DEV_OUTFITS:
        if data["image_url"] in existing:
            continue
        outfit = ScrapedOutfit(
            user_id=uid,
            image_url=data["image_url"],
            title=data["title"],
            brand=data.get("brand"),
            price=data.get("price"),
            source_url=data["source_url"],
            source_domain=data.get("source_domain"),
            category=data["category"],
            tags=data["tags"],
            style_tags=data["tags"],
            weather_tags=[],
        )
        db.add(outfit)
        existing.add(data["image_url"])
        added += 1
    if added > 0:
        await db.commit()
    return added


@router.get("/outfits", response_model=DiscoverBatchResponse)
async def get_discover_outfits(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force fetch new outfits"),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    uid = uuid.UUID(current_user_id)

    # Return whatever is already in the DB immediately
    if not force:
        unseen = await _fetch_unseen(uid, db)
        if unseen:
            results = unseen[:BATCH_SIZE]
            return DiscoverBatchResponse(
                outfits=[ScrapedOutfitOut.model_validate(o) for o in results],
                total=len(results),
                has_more=len(unseen) > BATCH_SIZE,
            )

    # No outfits yet — seed dev outfits instantly, kick off real scraping in background
    user = await db.get(User, uid)
    if not user:
        # JWT valid but user was deleted (e.g. DB reset) — force re-auth
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="User not found, re-authenticate")

    await _seed_dev_outfits(uid, db)

    # Kick off real scraping in background (won't block this response)
    background_tasks.add_task(_seed_real_outfits, uid)

    unseen = await _fetch_unseen(uid, db)

    # All seen — rank by style match instead of random replay.
    if not unseen:
        # Collect preferred tags from what the user liked.
        liked_rows = (await db.scalars(
            select(ScrapedOutfit)
            .where(ScrapedOutfit.user_id == uid, ScrapedOutfit.is_liked.is_(True))
        )).all()
        preferred_tags: set[str] = set()
        for o in liked_rows:
            if o.style_tags:
                preferred_tags.update(o.style_tags)

        # Reset all to unseen.
        await db.execute(
            update(ScrapedOutfit)
            .where(ScrapedOutfit.user_id == uid)
            .values(is_liked=None, seen_at=None)
        )
        await db.commit()

        # Fetch all and sort by tag overlap (most matching first).
        all_rows = list((await db.scalars(
            select(ScrapedOutfit).where(ScrapedOutfit.user_id == uid)
        )).all())

        if preferred_tags:
            def _overlap(o: ScrapedOutfit) -> int:
                return len(set(o.style_tags or []) & preferred_tags)
            all_rows.sort(key=_overlap, reverse=True)

        unseen = all_rows

    results = unseen[:BATCH_SIZE]
    return DiscoverBatchResponse(
        outfits=[ScrapedOutfitOut.model_validate(o) for o in results],
        total=len(results),
        has_more=len(unseen) > BATCH_SIZE,
    )


@router.post("/outfits/{outfit_id}/like", response_model=LikeOutfitResponse)
async def like_outfit(
    outfit_id: uuid.UUID,
    body: LikeOutfitRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    uid = uuid.UUID(current_user_id)
    outfit = await db.get(ScrapedOutfit, outfit_id)
    if not outfit or outfit.user_id != uid:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Outfit not found")

    outfit.is_liked = body.liked
    outfit.seen_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()

    action = "liked" if body.liked else "disliked"
    return LikeOutfitResponse(
        id=outfit.id,
        is_liked=body.liked,
        message=f"Outfit {action}",
    )


@router.get("/outfits/liked", response_model=LikedOutfitsResponse)
async def get_liked_outfits(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    uid = uuid.UUID(current_user_id)
    outfits = (
        await db.scalars(
            select(ScrapedOutfit)
            .where(ScrapedOutfit.user_id == uid, ScrapedOutfit.is_liked.is_(True))
            .order_by(ScrapedOutfit.updated_at.desc())
        )
    ).all()

    return LikedOutfitsResponse(
        outfits=[ScrapedOutfitOut.model_validate(o) for o in outfits],
        total=len(outfits),
    )
