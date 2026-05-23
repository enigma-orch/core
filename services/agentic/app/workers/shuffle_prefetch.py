"""
Shuffle prefetch worker — pre-generates outfit suggestions with try-on preview
images for every active user, so GET /shuffle can return fully rendered results
instantly instead of waiting on wan2.7-image at request time.

──────────────────────────────────────────────────────────────────────────────
How it works
──────────────────────────────────────────────────────────────────────────────

Scheduled run (every 60 min via APScheduler):

  For each user that has wardrobe items AND an avatar_url:

  1. Skip if no item has been updated since the last prefetch batch.
     This avoids re-generating identical suggestions when the wardrobe is
     unchanged.

  2. Run the same candidate-ranking logic as GET /shuffle:
       - filter items to the current season
       - rank within each category by cosine similarity to the user's taste
         vector (liked / worn outfits), falling back to wear_count
       - assemble top + bottom (or dress) combos, layer in shoes / outerwear /
         accessories, score by taste similarity + recency penalty

  3. For each candidate:
       a. Pick a background color from the palette based on vibe / occasion.
       b. Pick a suggested song from recent Spotify tracks (valence × energy
          match) or the curated fallback map.
       c. Call the outfit agent (wan2.7-image via DashScope) to render a
          photorealistic try-on with the user's avatar.
       d. Upload the PNG to RustFS and record the preview URL.
       e. If image generation fails, persist the suggestion without a preview
          (the item grouping and metadata are still useful).

  4. Replace all previous suggestions for the user with the fresh batch
     (TTL = 24 hours from generation time).

GET /shuffle reads from outfit_suggestions first. It falls back to the
existing live logic (no preview images) only when no unexpired rows exist —
for example, users who have never had their suggestions pre-generated yet.

Manual trigger:
  POST /api/v1/shuffle/prefetch  fires prefetch_for_user in the background
  for the calling user, so they don't have to wait for the next hourly run.

──────────────────────────────────────────────────────────────────────────────
Concurrency note
──────────────────────────────────────────────────────────────────────────────

Users are processed sequentially. The outfit agent's ThreadPoolExecutor is
capped at 2 workers; processing one user at a time keeps the queue shallow and
avoids exhausting the DashScope rate limit. If user count grows significantly,
consider adding an asyncio.Semaphore here.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.outfit_agent import generate_outfit_image
from app.config import settings
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.storage import upload_file
from app.models.item import Item
from app.models.outfit_suggestion import OutfitSuggestion
from app.models.spotify import SpotifyTrack
from app.models.user import User
from app.repositories.outfit import OutfitRepository
from app.services.outfit_preview import build_items_description
from app.services.shuffle import (
    build_candidates,
    current_season,
    filter_by_season,
    pick_background_color,
    suggest_song,
)

logger = logging.getLogger(__name__)

_SUGGESTION_TTL_HOURS = 24
_CANDIDATES_PER_USER = 5


async def prefetch_for_user(user: User, db: AsyncSession, base_url: str) -> None:
    """Generate and persist fresh shuffle suggestions for a single user.

    Idempotent: deletes the user's previous suggestions before writing new
    ones, so the table never accumulates duplicate batches.

    Skips silently when:
    - the user has no wardrobe items
    - no item has been updated since the last prefetch (wardrobe unchanged)
    """
    items_rows = await db.scalars(select(Item).where(Item.user_id == user.id))
    items = list(items_rows.all())
    if not items:
        return

    # Skip if wardrobe is unchanged since last batch
    latest_item_ts: datetime = max(i.updated_at for i in items)
    if latest_item_ts.tzinfo is None:
        latest_item_ts = latest_item_ts.replace(tzinfo=timezone.utc)

    latest_suggestion_ts: datetime | None = await db.scalar(
        select(func.max(OutfitSuggestion.created_at)).where(
            OutfitSuggestion.user_id == user.id
        )
    )
    if latest_suggestion_ts is not None:
        if latest_suggestion_ts.tzinfo is None:
            latest_suggestion_ts = latest_suggestion_ts.replace(tzinfo=timezone.utc)
        if latest_item_ts <= latest_suggestion_ts:
            logger.debug("shuffle_prefetch: skipping user %s — wardrobe unchanged", user.id)
            return

    season = current_season()
    seasonal_items = filter_by_season(items, season) or items

    outfit_repo = OutfitRepository(db, user.id)
    taste = await outfit_repo.get_taste_vector()

    candidates = build_candidates(
        items=seasonal_items,
        taste=taste,
        target_occasion=None,
        limit=_CANDIDATES_PER_USER,
    )
    if not candidates:
        return

    # Fetch recent Spotify tracks once for the whole batch (best-effort)
    spotify_tracks: list[tuple[str, str, float | None, float | None]] | None = None
    if user.spotify_id:
        try:
            rows = await db.scalars(
                select(SpotifyTrack)
                .where(SpotifyTrack.user_id == user.id)
                .order_by(SpotifyTrack.played_at.desc())
                .limit(20)
            )
            spotify_tracks = [
                (t.track_name, t.artist_name, t.valence, t.energy)
                for t in rows.all()
            ]
        except Exception as exc:
            logger.warning("shuffle_prefetch: Spotify fetch failed for user %s: %s", user.id, exc)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=_SUGGESTION_TTL_HOURS)

    # Replace previous suggestions for this user
    await db.execute(delete(OutfitSuggestion).where(OutfitSuggestion.user_id == user.id))

    for candidate in candidates:
        dominant_vibe = next((it.vibe for it in candidate.items if it.vibe), None)
        dominant_mood = next((it.mood for it in candidate.items if it.mood), None)
        bg_color = pick_background_color(dominant_vibe, None)
        song = suggest_song(dominant_mood, dominant_vibe, spotify_tracks)

        preview_url: str | None = None
        item_image_urls = [it.clean_image_url for it in candidate.items if it.clean_image_url]

        if user.avatar_url and item_image_urls:
            try:
                description = build_items_description(list(candidate.items))
                image_bytes = await generate_outfit_image(
                    user.avatar_url, item_image_urls, description, bg_color
                )
                key = f"wardrobe/shuffle/{uuid.uuid4()}.png"
                upload_file(key, image_bytes, content_type="image/png")
                preview_url = f"{base_url}/api/v1/wardrobe/files/{key}"
            except Exception as exc:
                logger.warning(
                    "shuffle_prefetch: image generation failed for user %s: %s", user.id, exc
                )

        db.add(OutfitSuggestion(
            user_id=user.id,
            item_ids=[str(i) for i in candidate.item_ids],
            preview_image_url=preview_url,
            season=season,
            score=candidate.score,
            vibe=dominant_vibe,
            mood=dominant_mood,
            background_color=bg_color,
            suggested_song=song,
            expires_at=expires_at,
        ))

    await db.flush()
    logger.info(
        "shuffle_prefetch: persisted %d suggestions for user %s (preview=%s)",
        len(candidates),
        user.id,
        "yes" if preview_url else "no",
    )


async def scheduled_shuffle_prefetch() -> None:
    """APScheduler entry point — processes all eligible users sequentially."""
    logger.info("shuffle_prefetch: batch starting")
    base_url = settings.public_url.rstrip("/")

    async with AsyncSessionLocal() as db:
        users = (
            await db.scalars(select(User).where(User.avatar_url.is_not(None)))
        ).all()

        attempted = failed = 0
        for user in users:
            try:
                await prefetch_for_user(user, db, base_url)
                attempted += 1
            except Exception as exc:
                logger.error(
                    "shuffle_prefetch: unhandled error for user %s: %s", user.id, exc
                )
                failed += 1

        await db.commit()

    logger.info(
        "shuffle_prefetch: batch done — attempted=%d failed=%d", attempted, failed
    )
