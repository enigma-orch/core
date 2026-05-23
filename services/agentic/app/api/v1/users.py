"""User profile endpoints."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.storage import upload_file
from app.models.user import User
from app.schemas.user import UserMeOut
from app.services.jwt import get_current_user_id_verified

router = APIRouter(prefix="/users", tags=["users"])

AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _avatar_storage_url(base_url: str, key: str) -> str:
    return f"{base_url}/api/v1/wardrobe/files/{key}"


@router.get("/me", response_model=UserMeOut, summary="Get the authenticated user's full profile")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
):
    user = await db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserMeOut.from_user(user)


@router.patch("/me/avatar", response_model=UserMeOut, summary="Upload or replace the user's profile photo")
async def upload_avatar(
    request: Request,
    image: UploadFile = File(..., description="Profile photo (JPEG, PNG, or WEBP, max 5 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
):
    if image.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{image.content_type}'. Allowed: JPEG, PNG, WEBP.",
        )

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5 MB.")

    ext = (image.content_type or "image/jpeg").split("/")[-1].replace("jpeg", "jpg")
    key = f"avatars/{current_user_id}/{uuid.uuid4()}.{ext}"
    upload_file(key, data, content_type=image.content_type or "image/jpeg", bucket=request.app.state.rustfs_bucket)

    avatar_url = _avatar_storage_url(str(request.base_url).rstrip("/"), key)

    user = await db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.avatar_url = avatar_url
    await db.flush()
    await db.refresh(user)

    return UserMeOut.from_user(user)

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.storage import upload_file
from app.models.user import User
from app.schemas.user import UserOut
from app.services.background_removal import ALLOWED_CONTENT_TYPES, MAX_BYTES
from app.services.jwt import get_current_user_id_verified

router = APIRouter(prefix="/users", tags=["users"])

_AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5 MB — tighter than wardrobe items


def _avatar_key(user_id: str, filename: str | None) -> str:
    ext = Path(filename).suffix.lstrip(".").lower() if filename else "jpg"
    ext = ext if ext in {"jpg", "jpeg", "png", "webp"} else "jpg"
    # Deterministic per-user key so re-uploads overwrite in place.
    return f"avatars/{user_id}.{ext}"


@router.post("/me/avatar", response_model=UserOut, summary="Upload profile picture")
async def upload_avatar(
    request: Request,
    image: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id_verified),
) -> UserOut:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported type '{image.content_type}'. Accepted: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > _AVATAR_MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    key = _avatar_key(current_user_id, image.filename)
    upload_file(key, data, content_type=image.content_type, bucket=request.app.state.rustfs_bucket)

    base = str(request.base_url).rstrip("/")
    avatar_url = f"{base}/api/v1/wardrobe/files/{key}"

    user = await db.get(User, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.avatar_url = avatar_url
    await db.flush()
    await db.refresh(user)
    return UserOut.model_validate(user)
