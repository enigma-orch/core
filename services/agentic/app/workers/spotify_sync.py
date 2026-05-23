"""
Background worker — fetches the user's 5 most recently saved Spotify tracks,
stores them, updates audio features, then recalculates mood.

Runs every 24 hours via APScheduler.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import AsyncSessionLocal
from app.models.spotify import SpotifyTrack
from app.models.user import User
from app.services import spotify as spotify_svc
from app.services.mood import extract_mood

logger = logging.getLogger(__name__)


async def _ensure_fresh_token(user: User, session: AsyncSession) -> str | None:
    """Refresh token if expired; return current access token or None."""
    if not user.spotify_access_token or not user.spotify_refresh_token:
        return None

    now = datetime.now(timezone.utc)
    if user.spotify_token_expires_at and user.spotify_token_expires_at > now:
        return user.spotify_access_token

    try:
        data = await spotify_svc.refresh_access_token(user.spotify_refresh_token)
        user.spotify_access_token = data["access_token"]
        user.spotify_token_expires_at = spotify_svc.token_expires_at(data["expires_in"])
        # Spotify may rotate the refresh token
        if "refresh_token" in data:
            user.spotify_refresh_token = data["refresh_token"]
        await session.flush()
        return user.spotify_access_token
    except Exception as exc:
        logger.warning("Token refresh failed for user %s: %s", user.id, exc)
        return None


async def sync_user(user: User, session: AsyncSession) -> None:
    access_token = await _ensure_fresh_token(user, session)
    if not access_token:
        return

    try:
        items = await spotify_svc.get_my_tracks(access_token, limit=5)
    except Exception as exc:
        logger.warning("Failed to fetch saved tracks for user %s: %s", user.id, exc)
        return

    if not items:
        return

    tracks_for_mood: list[SpotifyTrack] = []
    for item in items:
        track = item.get("track", {})
        spotify_track_id = track.get("id")
        if not spotify_track_id:
            continue

        added_at_str = item.get("added_at")
        played_at = (
            datetime.fromisoformat(added_at_str.replace("Z", "+00:00"))
            if added_at_str
            else datetime.now(timezone.utc)
        )

        # Skip if we already have this exact track saved at this time
        existing = await session.scalar(
            select(SpotifyTrack).where(
                SpotifyTrack.user_id == user.id,
                SpotifyTrack.spotify_track_id == spotify_track_id,
                SpotifyTrack.played_at == played_at,
            )
        )
        if existing:
            tracks_for_mood.append(existing)
            continue

        images = track.get("album", {}).get("images", [])
        st = SpotifyTrack(
            user_id=user.id,
            spotify_track_id=spotify_track_id,
            track_name=track.get("name", ""),
            artist_name=", ".join(a["name"] for a in track.get("artists", [])),
            album_name=track.get("album", {}).get("name"),
            album_image_url=images[0]["url"] if images else None,
            played_at=played_at,
        )
        session.add(st)
        tracks_for_mood.append(st)

    # Fetch audio features for tracks that don't have them yet
    need_features = [t for t in tracks_for_mood if t.valence is None and t.spotify_track_id]
    if need_features:
        try:
            features = await spotify_svc.get_audio_features(
                access_token, [t.spotify_track_id for t in need_features]
            )
            feat_map = {f["id"]: f for f in features if f}
            for t in need_features:
                f = feat_map.get(t.spotify_track_id, {})
                t.valence = f.get("valence")
                t.energy = f.get("energy")
                t.danceability = f.get("danceability")
                t.tempo = f.get("tempo")
        except Exception as exc:
            logger.warning("Audio features fetch failed for user %s: %s", user.id, exc)

    await session.flush()

    # Derive mood solely from these 5 tracks
    user.mood = extract_mood(tracks_for_mood)
    logger.info("User %s mood updated to %s (from %d tracks)", user.id, user.mood, len(tracks_for_mood))


async def sync_all_users() -> None:
    async with AsyncSessionLocal() as session:
        users = (await session.scalars(select(User).where(User.spotify_id.is_not(None)))).all()
        for user in users:
            await sync_user(user, session)
        await session.commit()
