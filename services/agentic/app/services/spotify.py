"""Spotify OAuth + API helpers."""
from __future__ import annotations

import base64
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import httpx

from app.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.user import User

_AUDIO_FEATURES_TTL = 24 * 3600  # audio features never change for a track

_features_cache: dict[str, tuple[float, dict[str, Any]]] = {}

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-read-recently-played",
    "user-library-read",
]


def build_auth_redirect_url(state: str, redirect_uri: str | None = None) -> str:
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri or settings.spotify_redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return f"{SPOTIFY_AUTH_URL}?{urllib.parse.urlencode(params)}"


def _basic_auth_header() -> str:
    raw = f"{settings.spotify_client_id}:{settings.spotify_client_secret}"
    return "Basic " + base64.b64encode(raw.encode()).decode()


async def exchange_code(code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri or settings.spotify_redirect_uri,
            },
            headers={"Authorization": _basic_auth_header()},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            headers={"Authorization": _basic_auth_header()},
        )
        resp.raise_for_status()
        return resp.json()


def token_expires_at(expires_in: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=expires_in)


async def get_current_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not resp.is_success:
            raise Exception(f"Spotify /me returned {resp.status_code}: {resp.text}")
        return resp.json()


async def get_my_tracks(access_token: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fetch the user's most recently saved tracks (max 5)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me/tracks",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json().get("items", [])


async def get_audio_features(access_token: str, track_ids: list[str]) -> list[dict[str, Any]]:
    if not track_ids:
        return []

    # Per-track cache — audio features are immutable, so dedupe across users.
    now = time.monotonic()
    missing = []
    out_map: dict[str, dict[str, Any] | None] = {}
    for tid in track_ids:
        cached = _features_cache.get(tid)
        if cached and (now - cached[0]) < _AUDIO_FEATURES_TTL:
            out_map[tid] = cached[1]
        else:
            missing.append(tid)

    if missing:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SPOTIFY_API_BASE}/audio-features",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"ids": ",".join(missing)},
            )
            resp.raise_for_status()
            fetched = resp.json().get("audio_features", [])
        for f in fetched:
            if not f:
                continue
            _features_cache[f["id"]] = (now, f)
            out_map[f["id"]] = f

    return [out_map.get(tid) for tid in track_ids if out_map.get(tid)]


# ── Token management ──────────────────────────────────────────────────────────

async def ensure_fresh_token(user: "User", db: "AsyncSession") -> str:
    """Return a valid access token, refreshing via Spotify if it has expired.

    Updates user.spotify_access_token and user.spotify_token_expires_at in the
    DB session (caller must commit or flush).
    """
    now = datetime.now(timezone.utc)
    expires_at = user.spotify_token_expires_at
    token_is_stale = expires_at is None or expires_at <= now

    if token_is_stale and user.spotify_refresh_token:
        data = await refresh_access_token(user.spotify_refresh_token)
        user.spotify_access_token = data["access_token"]
        user.spotify_token_expires_at = token_expires_at(data.get("expires_in", 3600))
        if data.get("refresh_token"):
            user.spotify_refresh_token = data["refresh_token"]
        await db.flush()

    return user.spotify_access_token


# ── Playlist fetching ─────────────────────────────────────────────────────────

async def get_user_playlists(access_token: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch the user's saved/followed playlists from Spotify.

    Returns a list of playlist objects with at least:
      id, name, tracks.total, images[]
    """
    pass  # TODO


# ── Top tracks & artists ──────────────────────────────────────────────────────

async def get_top_tracks(
    access_token: str,
    time_range: str = "short_term",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Fetch the user's top tracks from Spotify.

    time_range: "short_term" (~4 weeks), "medium_term" (~6 months), "long_term" (all time).
    Each item includes id, name, artists[], album, and audio features are fetched
    separately via get_audio_features().
    """
    pass  # TODO


async def get_top_artists(
    access_token: str,
    time_range: str = "short_term",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch the user's top artists from Spotify.

    Each item includes id, name, genres[], popularity.
    genres[] is the main signal used to map music taste → style vibes in the
    shuffle engine.
    """
    pass  # TODO


# ── Taste profile assembly ────────────────────────────────────────────────────

async def build_taste_profile(access_token: str) -> "SpotifyTasteProfile":
    """Aggregate playlists, top tracks, top artists, and audio features into a
    single SpotifyTasteProfile that shuffle and outfit compose can consume.

    Steps (all best-effort — individual failures return empty lists/None):
    1. get_user_playlists     → PlaylistSummary[]
    2. get_top_tracks         → TrackSummary[] + audio features via get_audio_features()
    3. get_top_artists        → deduplicated genre list
    4. Average the audio features → AudioProfile
    """
    from app.schemas.spotify import AudioProfile, SpotifyTasteProfile

    pass  # TODO


# ── Taste → style mapping (used by shuffle scoring) ──────────────────────────

# Maps Spotify artist genres to the style vibe vocabulary used in Item.vibe.
# Extend this table as more genre→vibe relationships are identified.
GENRE_TO_VIBE: dict[str, str] = {
    "hip hop": "streetwear",
    "rap": "streetwear",
    "trap": "streetwear",
    "r&b": "bold",
    "soul": "elegant",
    "jazz": "elegant",
    "classical": "formal",
    "pop": "minimal",
    "indie pop": "minimal",
    "electronic": "edgy",
    "techno": "edgy",
    "house": "sporty",
    "dance pop": "sporty",
    "country": "casual",
    "folk": "casual",
    "rock": "edgy",
    "metal": "edgy",
    "latin": "bold",
    "reggaeton": "bold",
}


def genres_to_vibes(genres: list[str]) -> list[str]:
    """Map a list of Spotify artist genres to style vibes.

    Returns deduplicated vibes in order of frequency.
    """
    counts: dict[str, int] = {}
    for g in genres:
        gl = g.lower()
        for keyword, vibe in GENRE_TO_VIBE.items():
            if keyword in gl:
                counts[vibe] = counts.get(vibe, 0) + 1
    return sorted(counts, key=lambda v: -counts[v])
