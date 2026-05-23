"""Background-removal service.

remove.bg is the primary backend (better quality, no GPU needed). When
the key is missing, quota is exhausted, or the API errors out, we fall
back to a local rembg inference call so uploads keep working.

The rembg session is expensive to construct (~1s, loads ONNX weights)
so it lives on app.state — initialised once in main.py's lifespan and
reused for every request.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from app.config import settings
from app.infrastructure.storage import upload_file

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB

_executor = ThreadPoolExecutor(max_workers=2)

# Bound at startup by main.py — holds the rembg session (or None if unavailable).
_rembg_session: Any | None = None


def init_rembg_session() -> Any | None:
    """Create a rembg session for the configured model. Returns None on failure.

    Called once during FastAPI startup so the first upload doesn't pay the
    ONNX cold-start cost.
    """
    global _rembg_session
    try:
        from rembg import new_session  # type: ignore
        _rembg_session = new_session("u2net")
        logger.info("rembg local fallback ready (u2net)")
    except Exception as exc:
        logger.warning("rembg session init failed; only remove.bg will be available: %s", exc)
        _rembg_session = None
    return _rembg_session


def _rembg_local_sync(image_bytes: bytes) -> bytes:
    if _rembg_session is None:
        raise RuntimeError("rembg session not initialised")
    from rembg import remove  # type: ignore
    return remove(image_bytes, session=_rembg_session)


async def _rembg_local(image_bytes: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _rembg_local_sync, image_bytes)


async def _remove_bg_api(image_bytes: bytes) -> bytes:
    """Call remove.bg. Raises RuntimeError on any failure so the caller can fall back."""
    if not settings.remove_bg_api_key:
        raise RuntimeError("REMOVE_BG_API_KEY is not configured")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.remove_bg_endpoint,
                headers={"X-Api-Key": settings.remove_bg_api_key},
                files={"image_file": ("image.png", image_bytes)},
                data={"size": "auto"},
            )
    except httpx.TimeoutException as exc:
        raise RuntimeError("remove.bg request timed out") from exc

    if resp.status_code == 402:
        raise RuntimeError("remove.bg quota exceeded — check your plan")
    if resp.status_code == 403:
        raise RuntimeError("remove.bg authentication failed — check REMOVE_BG_API_KEY")
    if not resp.is_success:
        raise RuntimeError(f"remove.bg error {resp.status_code}: {resp.text[:200]}")
    if not resp.content:
        raise RuntimeError("remove.bg returned an empty response")
    return resp.content


async def remove_bg(image_bytes: bytes) -> bytes:
    """Return transparent PNG bytes. Tries remove.bg first, then local rembg."""
    try:
        return await _remove_bg_api(image_bytes)
    except Exception as exc:
        if _rembg_session is None:
            # Nothing to fall back to — surface the original error.
            raise
        logger.warning("remove.bg failed (%s); falling back to local rembg", exc)
        return await _rembg_local(image_bytes)


async def process_image(image_bytes: bytes, bucket: str) -> str:
    """Remove background, upload PNG to RustFS, return storage key."""
    png_bytes = await remove_bg(image_bytes)
    key = f"wardrobe/no-bg/{uuid.uuid4()}.png"
    upload_file(key, png_bytes, content_type="image/png", bucket=bucket)
    return key
