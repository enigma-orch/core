"""Social graph: follows + style pulse feed."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.follow import Follow
from app.models.outfit import Outfit
from app.models.user import User
from app.schemas.social import FollowOut, FriendOutfitPreview, StylePulseOut
from app.services.jwt import get_current_user_id_verified

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/follows", response_model=list[FollowOut])
async def list_follows(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> list[FollowOut]:
    uid = uuid.UUID(current_user_id)
    rows = (
        await db.execute(
            select(Follow.followee_id, Follow.created_at, User.display_name, User.avatar_url, User.location)
            .join(User, User.id == Follow.followee_id)
            .where(Follow.follower_id == uid)
            .order_by(Follow.created_at.desc())
        )
    ).all()
    return [
        FollowOut(
            user_id=row.followee_id,
            display_name=row.display_name,
            avatar_url=row.avatar_url,
            location=row.location,
            followed_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/follows/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def follow_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> Response:
    uid = uuid.UUID(current_user_id)
    if uid == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = pg_insert(Follow.__table__).values(
        follower_id=uid, followee_id=user_id
    ).on_conflict_do_nothing(index_elements=["follower_id", "followee_id"])
    await db.execute(stmt)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/follows/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> Response:
    uid = uuid.UUID(current_user_id)
    await db.execute(
        delete(Follow).where(
            and_(Follow.follower_id == uid, Follow.followee_id == user_id)
        )
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/style-pulse", response_model=StylePulseOut)
async def style_pulse(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> StylePulseOut:
    uid = uuid.UUID(current_user_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        await db.execute(
            select(Outfit, User)
            .join(Follow, Follow.followee_id == Outfit.user_id)
            .join(User, User.id == Outfit.user_id)
            .where(
                Follow.follower_id == uid,
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
