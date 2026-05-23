from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database import get_db

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

_bearer = HTTPBearer()


def _assert_secret_safe() -> None:
    """Refuse to operate with a default/empty secret in non-development envs."""
    if settings.app_env != "development" and settings.secret_key in ("", "change-me", "change-me-in-production"):
        raise RuntimeError(
            "settings.secret_key is unset or default; refusing to mint tokens. "
            "Set SECRET_KEY in the environment."
        )


def create_access_token(user_id: uuid.UUID) -> str:
    _assert_secret_safe()
    payload = {
        "sub": str(user_id),
        "typ": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token() -> tuple[str, str, datetime]:
    """Return (plaintext_token, sha256_hash, expires_at). Caller stores the hash."""
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return token, hash_refresh_token(token), expires_at


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("typ") not in (None, "access"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")
    return payload["sub"]


async def get_current_user_id_verified(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Decode the JWT and confirm the user exists in the DB. Returns 401 if not."""
    from app.models.user import User  # local import to avoid circular dependency

    user_id_str = decode_access_token(credentials.credentials)
    exists = await db.scalar(
        select(User.id).where(User.id == uuid.UUID(user_id_str))
    )
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found — please log in again",
        )
    return user_id_str


# Backwards-compatible alias — callers should migrate to the verified variant.
# Kept as a thin wrapper so existing imports keep working.
get_current_user_id = get_current_user_id_verified
