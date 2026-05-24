"""Spotify + Google Calendar OAuth endpoints."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("spotify")

from app.config import settings
from app.infrastructure.database import get_db
from app.models.onboarding import ColorPalette, Store, Vibe
from app.models.user import User
from app.repositories.clothing import ClothingItemRepository
from app.schemas.onboarding import ColorPaletteOut, StoreOut, VibeOut
from app.schemas.user import AuthMeOut, RefreshRequest, RefreshResponse, TokenResponse, UserOut
from app.services import google_calendar as gcal_svc
from app.services import spotify as spotify_svc
from app.services.jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    get_current_user_id_verified,
    hash_refresh_token,
)
from app.workers.spotify_sync import sync_user


async def _issue_tokens(user: User, db: AsyncSession) -> tuple[str, str]:
    """Mint access + refresh tokens, persist the refresh hash on the user."""
    access = create_access_token(user.id)
    refresh, refresh_hash, refresh_expires = create_refresh_token()
    user.refresh_token_hash = refresh_hash
    user.refresh_token_expires_at = refresh_expires
    await db.flush()
    return access, refresh


def _sign_state(user_id: str) -> str:
    """Build an HMAC-signed state token: <user_id>.<nonce>.<sig>"""
    nonce = secrets.token_urlsafe(8)
    payload = f"{user_id}.{nonce}"
    sig = hmac.new(
        settings.secret_key.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{sig}"


def _verify_state(state: str) -> str:
    """Verify an HMAC-signed state token and return the user_id."""
    parts = state.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Malformed state parameter")
    user_id, nonce, sig = parts
    expected = hmac.new(
        settings.secret_key.encode(),
        f"{user_id}.{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="Invalid state signature")
    return user_id

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Guest login — no credentials required
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=RefreshResponse, summary="Rotate refresh token for a new access token")
async def refresh_tokens(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone

    token_hash = hash_refresh_token(body.refresh_token)
    user = await db.scalar(select(User).where(User.refresh_token_hash == token_hash))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if user.refresh_token_expires_at and user.refresh_token_expires_at < datetime.now(timezone.utc):
        # Invalidate even on the off chance the hash collides with a stale row.
        user.refresh_token_hash = None
        user.refresh_token_expires_at = None
        await db.flush()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    access, new_refresh = await _issue_tokens(user, db)
    return RefreshResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=204, summary="Invalidate the current refresh token")
async def logout(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
):
    user = await db.get(User, current_user_id)
    if user:
        user.refresh_token_hash = None
        user.refresh_token_expires_at = None
        await db.flush()


@router.get("/me", response_model=AuthMeOut, summary="Get the authenticated user's full context")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> AuthMeOut:
    """
    Returns the complete user profile including resolved vibe, color palette,
    and store objects. Use this on app launch to hydrate the full user state
    in a single request.
    """
    user = await db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    slugs_vibes = user.preferred_styles or []
    slugs_colors = user.preferred_colors or []
    slugs_stores = user.preferred_stores or []

    vibes: list[VibeOut] = []
    color_palettes: list[ColorPaletteOut] = []
    stores: list[StoreOut] = []

    if slugs_vibes:
        rows = await db.scalars(select(Vibe).where(Vibe.slug.in_(slugs_vibes)))
        vibe_map = {v.slug: v for v in rows.all()}
        vibes = [VibeOut.model_validate(vibe_map[s]) for s in slugs_vibes if s in vibe_map]

    if slugs_colors:
        rows = await db.scalars(select(ColorPalette).where(ColorPalette.slug.in_(slugs_colors)))
        palette_map = {p.slug: p for p in rows.all()}
        color_palettes = [ColorPaletteOut.model_validate(palette_map[s]) for s in slugs_colors if s in palette_map]

    if slugs_stores:
        rows = await db.scalars(select(Store).where(Store.slug.in_(slugs_stores)))
        store_map = {s.slug: s for s in rows.all()}
        stores = [StoreOut.model_validate(store_map[s]) for s in slugs_stores if s in store_map]

    return AuthMeOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        mood=user.mood,
        vibes=vibes,
        color_palettes=color_palettes,
        stores=stores,
        preferred_styles=user.preferred_styles,
        preferred_colors=user.preferred_colors,
        preferred_stores=user.preferred_stores,
        location=user.location,
        style_identity=user.style_identity,
        tops_size=user.tops_size,
        bottoms_size=user.bottoms_size,
        shoes_size=user.shoes_size,
        outerwear_size=user.outerwear_size,
        budget_min=user.budget_min,
        budget_max=user.budget_max,
        spotify_id=user.spotify_id,
        has_spotify=user.spotify_id is not None,
        has_google_calendar=user.google_access_token is not None,
        google_calendar_id=user.google_calendar_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/guest", response_model=TokenResponse, summary="Create a guest session")
async def guest_login(db: AsyncSession = Depends(get_db)):
    """
    Creates a temporary guest user with no Spotify/Google links and returns
    a JWT so the app is usable before the user connects their accounts.
    """
    user = User(display_name="Guest")
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Auto-seed demo wardrobe so the app is usable immediately
    clothing_repo = ClothingItemRepository(db, user.id)
    await clothing_repo.seed_demo()

    access, refresh = await _issue_tokens(user, db)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


# ---------------------------------------------------------------------------
# Spotify — step 1: login
# ---------------------------------------------------------------------------

@router.get("/spotify", summary="Redirect to Spotify consent screen")
async def spotify_login():
    state = secrets.token_urlsafe(16)
    return RedirectResponse(spotify_svc.build_auth_redirect_url(state))


@router.get("/spotify/callback", summary="Spotify OAuth callback")
async def spotify_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    1. Exchange code → tokens
    2. Upsert user in DB
    3. Kick off an immediate Spotify sync for this user
    4. Redirect to drip://auth?token=<jwt> so the iOS app can capture the JWT
       via ASWebAuthenticationSession.
    """
    try:
        token_data = await spotify_svc.exchange_code(code)
    except Exception as exc:
        logger.exception("Spotify token exchange failed")
        raise HTTPException(status_code=400, detail=f"Spotify token exchange failed: {exc}")

    logger.info("Token exchange OK, keys=%s", list(token_data.keys()))

    if "access_token" not in token_data:
        logger.error("Token response missing access_token: %s", token_data)
        raise HTTPException(status_code=400, detail=f"Spotify returned unexpected response (no access_token): {token_data}")

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_at = spotify_svc.token_expires_at(token_data.get("expires_in", 3600))

    try:
        profile = await spotify_svc.get_current_user(access_token)
    except Exception as exc:
        logger.exception("Spotify /me fetch failed")
        raise HTTPException(status_code=400, detail=f"Spotify profile fetch failed: {exc}")

    logger.info("Spotify /me OK, id=%s", profile.get("id"))

    spotify_id = profile["id"]
    email = next((e["address"] for e in profile.get("emails", []) if e.get("address")), None)

    user = await db.scalar(select(User).where(User.spotify_id == spotify_id))
    if not user:
        user = User(spotify_id=spotify_id)
        db.add(user)

    user.display_name = profile.get("display_name")
    user.email = user.email or email
    images = profile.get("images", [])
    user.avatar_url = images[0]["url"] if images else None
    user.spotify_access_token = access_token
    user.spotify_refresh_token = refresh_token or user.spotify_refresh_token
    user.spotify_token_expires_at = expires_at

    await db.flush()
    await db.refresh(user)

    # Immediate sync — don't wait, fire and forget
    import asyncio
    asyncio.create_task(sync_user(user, db))

    access, refresh = await _issue_tokens(user, db)
    # Redirect back to the iOS app via custom scheme — ASWebAuthenticationSession
    # intercepts this and delivers the URL to the Swift callback.
    return RedirectResponse(
        url=f"drip://auth?token={access}&refresh_token={refresh}",
        status_code=302,
    )


# ---------------------------------------------------------------------------
# Google Sign-In — verifies ID token from iOS GoogleSignInManager
# ---------------------------------------------------------------------------

from pydantic import BaseModel


class GoogleSignInRequest(BaseModel):
    id_token: str


@router.post("/google", summary="Verify Google ID token and return JWT")
async def google_signin(
    body: GoogleSignInRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the iOS app after GoogleSignInManager gets an ID token.
    Verifies the token with Google, upserts the user, and returns a JWT.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": body.id_token},
            )
            resp.raise_for_status()
            info = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {exc}")

    google_id = info.get("sub")
    email = info.get("email", "")
    name = info.get("name", "")
    picture = info.get("picture", "")

    user = await db.scalar(select(User).where(User.google_id == google_id))
    if not user:
        user = User(google_id=google_id, display_name=name, email=email or None)
        db.add(user)
    else:
        user.display_name = user.display_name or name
        user.email = user.email or email or None
    user.avatar_url = user.avatar_url or picture or None

    await db.flush()
    await db.refresh(user)

    access, refresh = await _issue_tokens(user, db)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )

# ---------------------------------------------------------------------------
# Google Calendar — link to an already-authenticated user (JWT required)
# ---------------------------------------------------------------------------

@router.get("/google/calendar/link", summary="Redirect to Google Calendar consent screen")
async def google_calendar_link(
    current_user_id: str = Depends(get_current_user_id_verified),
):
    """Initiate Calendar linking for the JWT-authenticated user.

    The state is HMAC-signed so the callback can trust the user_id without a
    DB lookup or session cookie.
    """
    state = _sign_state(current_user_id)
    return RedirectResponse(gcal_svc.build_auth_redirect_url(state))


@router.get("/google/callback", response_model=UserOut, summary="Google OAuth callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user_id = _verify_state(state)

    try:
        token_data = await gcal_svc.exchange_code(code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Google token exchange failed: {exc}")

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_at = gcal_svc.token_expires_at(token_data["expires_in"])

    try:
        userinfo = await gcal_svc.get_userinfo(access_token)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Google userinfo fetch failed: {exc}")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.google_id = userinfo.get("sub")
    user.email = user.email or userinfo.get("email")
    user.google_access_token = access_token
    user.google_refresh_token = refresh_token or user.google_refresh_token
    user.google_token_expires_at = expires_at
    user.google_calendar_id = "primary"

    await db.flush()
    await db.refresh(user)
    return user


@router.get("/google/calendars", summary="List user's Google Calendars")
async def list_calendars(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
):
    user = await db.get(User, current_user_id)
    if not user or not user.google_access_token:
        raise HTTPException(status_code=403, detail="Google Calendar not linked")
    try:
        calendars = await gcal_svc.list_calendars(user.google_access_token)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"calendars": calendars}
