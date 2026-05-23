"""Spotify OAuth + API helpers."""
from __future__ import annotations

import base64
import hashlib
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings

# Spotify rate-limits recently-played at ~50 reqs/sec across the app; cache
# per-user for 10 minutes so the 15-min worker sync still gets fresh data
# but ad-hoc calls (e.g. /compose) reuse it.
_RECENTLY_PLAYED_TTL = 10 * 60
_AUDIO_FEATURES_TTL = 24 * 3600  # audio features never change for a track

_recent_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_features_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _token_fingerprint(access_token: str) -> str:
    """Hash the access token so the cache key isn't itself the secret."""
    return hashlib.sha256(access_token.encode()).hexdigest()[:32]

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-read-recently-played",
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


async def get_recently_played(access_token: str, limit: int = 50) -> list[dict[str, Any]]:
    cache_key = f"{_token_fingerprint(access_token)}:{limit}"
    cached = _recent_cache.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < _RECENTLY_PLAYED_TTL:
        return cached[1]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me/player/recently-played",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": limit},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    _recent_cache[cache_key] = (time.monotonic(), items)
    return items


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
