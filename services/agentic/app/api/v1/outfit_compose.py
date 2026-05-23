"""POST /api/v1/wardrobe/outfits/compose — AI outfit composition endpoint."""
from __future__ import annotations

import logging
import uuid
from collections import Counter

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.outfit_agent import generate_outfit_image
from app.services.outfit_preview import build_items_description
from app.services.shuffle import pick_background_color
from app.infrastructure.database import get_db
from app.infrastructure.storage import upload_file
from app.models.item import Item
from app.models.outfit import Outfit
from app.models.outfit_item import OutfitItem
from app.models.spotify import SpotifyTrack
from app.models.user import User
from app.schemas.spotify import SpotifyTasteProfile
from app.schemas.wardrobe import ItemOut, OutfitComposeOut, OutfitComposeRequest
from app.services import embeddings as emb_svc
from app.services import spotify as spotify_svc
from app.services import weather as weather_svc
from app.services.jwt import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wardrobe/outfits", tags=["outfit-compose"])


async def _fetch_items(db: AsyncSession, item_ids: list[uuid.UUID]) -> list[Item]:
    rows = await db.scalars(select(Item).where(Item.id.in_(item_ids)))
    items = list(rows.all())
    missing = set(item_ids) - {i.id for i in items}
    if missing:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Items not found: {[str(m) for m in missing]}"},
        )
    return items


def _most_common(values: list[str | None]) -> str:
    cleaned = [v for v in values if v]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def _derive_metadata(items: list[Item]) -> dict:
    """Build outfit metadata from already-stored item fields — no AI call needed."""
    names = [i.name or i.category or "item" for i in items]
    outfit_name = " + ".join(names[:3])

    seasons = [s for i in items for s in (i.season or [])]
    occasion = _most_common([i.occasion for i in items])
    vibe = _most_common([i.vibe for i in items])
    mood = _most_common([i.mood for i in items])
    season = _most_common(seasons)

    return {
        "name": outfit_name,
        "vibe": vibe or "casual",
        "mood": mood or "confident",
        "season": season or "all-season",
        "occasion": occasion or "casual",
    }



def _outfit_embed_text(meta: dict, items: list[Item]) -> str:
    item_summaries = "; ".join(f"{i.category} {i.name}" for i in items if i.name)
    return (
        f"Outfit: {meta['name']}. Vibe: {meta['vibe']}. "
        f"Mood: {meta['mood']}. Season: {meta['season']}. "
        f"Occasion: {meta['occasion']}. Items: {item_summaries}."
    )


async def _spotify_snapshot(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    """Snapshot the user's last 3 played tracks with audio features, if any."""
    rows = await db.scalars(
        select(SpotifyTrack)
        .where(SpotifyTrack.user_id == user_id)
        .order_by(SpotifyTrack.played_at.desc())
        .limit(3)
    )
    tracks = list(rows.all())
    if not tracks:
        return None
    valences = [t.valence for t in tracks if t.valence is not None]
    energies = [t.energy for t in tracks if t.energy is not None]
    return {
        "recent_tracks": [
            {"track": t.track_name, "artist": t.artist_name}
            for t in tracks
        ],
        "avg_valence": round(sum(valences) / len(valences), 3) if valences else None,
        "avg_energy": round(sum(energies) / len(energies), 3) if energies else None,
    }


def _context_prompt_block(
    weather_str: str | None,
    mood: str | None,
    spotify: dict | None,
    taste_profile: SpotifyTasteProfile | None = None,
) -> str:
    parts: list[str] = []
    if weather_str:
        parts.append(f"Weather context: {weather_str}.")
    if mood and mood != "unknown":
        parts.append(f"Listener mood right now: {mood}.")
    if spotify and spotify.get("recent_tracks"):
        names = ", ".join(
            f"{t['track']} by {t['artist']}" for t in spotify["recent_tracks"][:2]
        )
        parts.append(f"Soundtrack: {names}.")
    if taste_profile:
        if taste_profile.top_genres:
            parts.append(f"Music genres: {', '.join(taste_profile.top_genres[:5])}.")
        ap = taste_profile.audio_profile
        if ap.avg_energy is not None:
            energy_label = "high-energy" if ap.avg_energy >= 0.6 else ("mellow" if ap.avg_energy <= 0.35 else "mid-tempo")
            parts.append(f"Current listening energy: {energy_label}.")
        if taste_profile.top_tracks:
            track_names = ", ".join(
                f"{t.name} by {', '.join(t.artists)}" for t in taste_profile.top_tracks[:2]
            )
            parts.append(f"Currently into: {track_names}.")
    if not parts:
        return ""
    return "\n\nADDITIONAL CONTEXT (use to inform styling — do NOT change identity):\n" + " ".join(parts)


@router.post("/compose", response_model=OutfitComposeOut, status_code=201)
async def compose_outfit(
    request: Request,
    body: OutfitComposeRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> OutfitComposeOut:
    user_id = uuid.UUID(current_user_id)
    if not body.item_ids:
        raise HTTPException(status_code=400, detail={"error": "item_ids must not be empty"})

    bucket = request.app.state.rustfs_bucket
    base_url = str(request.base_url).rstrip("/")

    # 1. Fetch items from DB (already processed during upload)
    items = await _fetch_items(db, body.item_ids)
    item_image_urls = [i.clean_image_url for i in items if i.clean_image_url]

    if not item_image_urls:
        raise HTTPException(status_code=400, detail={"error": "None of the items have a processed image"})

    # 2. Derive outfit metadata from item DB fields — no re-analysis needed
    meta = _derive_metadata(items)

    # 2b. Pull context for grounding + persistence (best-effort — never block compose).
    user = await db.get(User, user_id)
    weather_str: str | None = None
    if user and user.location:
        try:
            w = await weather_svc.get_weather(user.location)
            weather_str = f"{w.condition}, {int(w.temperature_c)}°C ({', '.join(w.tags)})"
        except Exception as exc:
            logger.warning("Weather lookup failed for user %s: %s", user_id, exc)
    mood = user.mood.value if user and user.mood else None
    spotify_snapshot = await _spotify_snapshot(db, user_id)

    taste_profile: SpotifyTasteProfile | None = None
    if user and user.spotify_id and user.spotify_access_token:
        try:
            token = await spotify_svc.ensure_fresh_token(user, db)
            taste_profile = await spotify_svc.build_taste_profile(token)
        except Exception as exc:
            logger.warning("Spotify taste profile unavailable for user %s: %s", user_id, exc)

    # 3. Build ground-truth item descriptions from DB to anchor the image generator
    items_description = build_items_description(items)
    items_description += _context_prompt_block(weather_str, mood, spotify_snapshot, taste_profile)

    # 4. Generate virtual try-on image: user photo + item images + metadata → wan2.7-image
    bg_color = pick_background_color(meta.get("vibe"), meta.get("occasion"))
    try:
        image_bytes = await generate_outfit_image(body.user_image_url, item_image_urls, items_description, bg_color)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "Image generation failed", "detail": str(exc)})

    # 5. Store generated image in RustFS
    try:
        preview_key = f"wardrobe/outfits/{uuid.uuid4()}.png"
        upload_file(preview_key, image_bytes, content_type="image/png", bucket=bucket)
        preview_url = f"{base_url}/api/v1/wardrobe/files/{preview_key}"
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "Image storage failed", "detail": str(exc)})

    # 5. Generate outfit embedding
    try:
        outfit_emb = await emb_svc.embed(_outfit_embed_text(meta, items))
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "Embedding failed", "detail": str(exc)})

    # 6. Persist Outfit
    now = datetime.now(timezone.utc)
    outfit = Outfit(
        user_id=user_id,
        name=meta["name"],
        preview_image_url=preview_url,
        occasion=meta["occasion"],
        season=meta["season"],
        vibe=meta["vibe"],
        mood=meta["mood"],
        weather_context=weather_str,
        spotify_context=spotify_snapshot,
        source="ai_generated",
        embedding=outfit_emb,
        worn_at=now,
        wear_count=1,
    )
    db.add(outfit)
    await db.flush()

    # 7. Link items to outfit
    for position, item in enumerate(items):
        db.add(OutfitItem(
            outfit_id=outfit.id,
            item_id=item.id,
            role=item.category,
            position=position,
        ))

    await db.flush()
    await db.refresh(outfit)

    out = OutfitComposeOut.model_validate(outfit)
    out.items = [ItemOut.model_validate(i) for i in items]
    return out
